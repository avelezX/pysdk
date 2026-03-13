"""
backfill_all_gaps.py — Backfill ALL missing market_marks from 2026-01-02 to today.

Uses Supabase Management API (SQL) to read source tables (the collector role
doesn't have SELECT on ibr_quotes_curve, sofr_swap_curve, etc.) and the REST
API to write market_marks (where collector has INSERT/UPDATE).

Usage:
    python backfill_all_gaps.py            # dry run (preview only)
    python backfill_all_gaps.py --commit   # actually store to DB
"""
import os
import sys
import json
from datetime import date, timedelta

import requests
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

import QuantLib as ql
import pandas as pd

from pricing.data.market_data import MarketDataLoader
from pricing.curves.curve_manager import CurveManager


# Date range
START_DATE = date(2026, 1, 2)
END_DATE   = date.today()

# Supabase Management API
PROJECT_REF = "tvpehjbqxpiswkqszwwv"
MGMT_URL = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"
ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")


def sql_query(query: str) -> list[dict]:
    """Execute SQL via Supabase Management API."""
    resp = requests.post(
        MGMT_URL,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"query": query},
    )
    resp.raise_for_status()
    return resp.json()


def business_days(start: date, end: date) -> list[str]:
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += timedelta(days=1)
    return days


def recalc_ndf(ndf_snapshot: dict, fx_spot: float) -> dict:
    """Re-derive F_market and deval_ea from fwd_pts_cop using new spot."""
    result = {}
    for months_str, v in ndf_snapshot.items():
        months = int(months_str)
        fwd_pts_cop = v["fwd_pts_cop"]
        f_market = fx_spot + fwd_pts_cop
        deval_ea = round(((f_market / fx_spot) ** (12 / months) - 1) * 100, 4)
        result[months_str] = {
            "fwd_pts_cop": round(fwd_pts_cop, 4),
            "F_market": round(f_market, 4),
            "deval_ea": deval_ea,
        }
    return result


def build_ibr_payload(cm: CurveManager) -> dict:
    return {k: round(v, 6) for k, v in cm.status()["ibr"]["nodes"].items()}


def build_sofr_payload(cm: CurveManager) -> dict:
    tenors = [1, 3, 6, 12, 18, 24, 36, 60, 84, 120, 180, 240, 360, 480, 600]
    payload = {}
    for m in tenors:
        dt = cm.valuation_date + ql.Period(m, ql.Months)
        payload[str(m)] = round(cm.sofr_zero_rate(dt) * 100, 6)
    return payload


# ── Bulk-load all source data upfront via SQL ──

def load_all_ibr() -> dict[str, dict]:
    """Load all IBR quotes, keyed by date string."""
    rows = sql_query("""
        SELECT fecha::date::text as d,
               ibr_1d, ibr_1m, ibr_3m, ibr_6m, ibr_12m,
               ibr_2y, ibr_5y, ibr_10y, ibr_15y, ibr_20y
        FROM xerenity.ibr_quotes_curve
        WHERE fecha >= '2026-01-01'
        ORDER BY fecha
    """)
    result = {}
    for r in rows:
        d = r.pop("d")
        # build_ibr_curve expects values as lists: {"ibr_1d": [9.638], ...}
        result[d] = {k: [float(v)] for k, v in r.items() if v is not None}
    return result


def load_all_sofr() -> dict[str, pd.DataFrame]:
    """Load all SOFR swap curves, keyed by date string."""
    rows = sql_query("""
        SELECT fecha::text as d, tenor_months, swap_rate
        FROM xerenity.sofr_swap_curve
        WHERE fecha >= '2026-01-01'
        ORDER BY fecha, tenor_months
    """)
    result = {}
    for r in rows:
        d = r["d"]
        if d not in result:
            result[d] = []
        result[d].append({"tenor_months": int(r["tenor_months"]), "swap_rate": float(r["swap_rate"])})
    return {d: pd.DataFrame(data) for d, data in result.items()}


def load_all_trm() -> dict[str, float]:
    """Load TRM (serie_id=25) for all dates."""
    rows = sql_query("""
        SELECT fecha::date::text as d, valor
        FROM xerenity.banrep_series_value_v2
        WHERE id_serie = 25 AND fecha >= '2026-01-01'
        ORDER BY fecha
    """)
    return {r["d"]: float(r["valor"]) for r in rows}


def load_all_sofr_on() -> dict[str, float]:
    """Load SOFR ON rates for all dates."""
    rows = sql_query("""
        SELECT fecha::text as d, rate
        FROM xerenity.us_reference_rates
        WHERE rate_type = 'SOFR' AND fecha >= '2026-01-01'
        ORDER BY fecha
    """)
    return {r["d"]: float(r["rate"]) / 100.0 for r in rows}


def load_all_cop_fwd() -> dict[str, pd.DataFrame]:
    """Load COP forward points for all dates."""
    rows = sql_query("""
        SELECT fecha::text as d, tenor, tenor_months, fwd_points, mid
        FROM xerenity.cop_fwd_points
        WHERE fecha >= '2026-01-01'
        ORDER BY fecha, tenor_months
    """)
    result = {}
    for r in rows:
        d = r["d"]
        if d not in result:
            result[d] = []
        result[d].append({
            "tenor": r["tenor"],
            "tenor_months": int(r["tenor_months"]) if r["tenor_months"] else None,
            "fwd_points": float(r["fwd_points"]) if r["fwd_points"] else None,
            "mid": float(r["mid"]) if r["mid"] else None,
        })
    return {d: pd.DataFrame(data) for d, data in result.items()}


def main():
    commit = "--commit" in sys.argv
    force  = "--force" in sys.argv
    dry_run = not commit

    loader = MarketDataLoader()

    print("Loading source data via Management API...")

    # ── Bulk load all source data ──
    all_ibr     = load_all_ibr()
    all_sofr    = load_all_sofr()
    all_trm     = load_all_trm()
    all_sofr_on = load_all_sofr_on()
    all_cop_fwd = load_all_cop_fwd()

    print(f"  IBR dates:     {len(all_ibr)}")
    print(f"  SOFR dates:    {len(all_sofr)}")
    print(f"  TRM dates:     {len(all_trm)}")
    print(f"  SOFR ON dates: {len(all_sofr_on)}")
    print(f"  COP fwd dates: {len(all_cop_fwd)}")
    print()

    # ── Get existing market_marks dates ──
    existing = loader._get("market_marks", "select=fecha&order=fecha.asc")
    existing_dates = {row["fecha"] for row in existing}

    # ── Load first mark as seed ──
    first_mark_date = min(existing_dates)
    seed = loader.fetch_marks(target_date=first_mark_date)
    if seed is None:
        raise RuntimeError(f"Cannot load seed from {first_mark_date}")

    last = {
        "fx_spot":  seed["fx_spot"],
        "sofr_on":  seed["sofr_on"],
        "ibr":      seed["ibr"],
        "sofr":     seed["sofr"],
        "ndf":      seed["ndf"],
    }

    bdays = business_days(START_DATE, END_DATE)

    print(f"market_marks: {len(existing_dates)} existing, {len(bdays)} business days total")
    print(f"Gaps to fill: {len([d for d in bdays if d not in existing_dates])} dates")
    print(f"Seed from: {first_mark_date} (fx_spot={last['fx_spot']})")
    print()
    print(f"{'fecha':<12} {'fx_spot':>10} {'sofr_on':>9} {'ibr_1d':>8} {'ibr_12m':>9} {'fills':>16}  status")
    print("-" * 90)

    stored = 0
    skipped = 0

    for fecha in bdays:
        # If this date already has a mark, update carry-forward state and skip
        if fecha in existing_dates and not force:
            mark = loader.fetch_marks(target_date=fecha)
            if mark:
                last["fx_spot"] = mark["fx_spot"]
                last["sofr_on"] = mark["sofr_on"]
                last["ibr"]     = mark["ibr"]
                last["sofr"]    = mark["sofr"]
                last["ndf"]     = mark["ndf"]
            skipped += 1
            continue

        fills = []

        # ── FX Spot: TRM from BanRep ──
        fx_spot = all_trm.get(fecha)
        if fx_spot is None:
            fx_spot = last["fx_spot"]
            fills.append("spot")

        # ── IBR: build curve ──
        ibr_quotes = all_ibr.get(fecha)
        cm = CurveManager()
        if ibr_quotes:
            try:
                cm.build_ibr_curve(ibr_quotes)
                ibr_payload = build_ibr_payload(cm)
            except Exception as e:
                ibr_payload = last["ibr"]
                fills.append("ibr")
        else:
            ibr_payload = last["ibr"]
            fills.append("ibr")

        # ── SOFR curve ──
        sofr_df = all_sofr.get(fecha, pd.DataFrame())
        if not sofr_df.empty:
            try:
                cm.build_sofr_curve(sofr_df)
                cm.set_fx_spot(fx_spot)
                sofr_payload = build_sofr_payload(cm)
            except Exception:
                sofr_payload = last["sofr"]
                fills.append("sofr")
        else:
            sofr_payload = last["sofr"]
            fills.append("sofr")

        # ── SOFR ON ──
        sofr_on = all_sofr_on.get(fecha)
        sofr_on_pct = round(sofr_on * 100, 6) if sofr_on else None
        if sofr_on_pct is None:
            sofr_on_pct = last["sofr_on"]
            fills.append("on")

        # ── NDF: use mid (outright forward) directly from cop_fwd_points ──
        cop_fwd = all_cop_fwd.get(fecha, pd.DataFrame())
        if not cop_fwd.empty:
            try:
                ndf_payload = {}
                for _, row in cop_fwd.iterrows():
                    months = int(row["tenor_months"]) if row["tenor_months"] else 0
                    if months <= 0 or row.get("mid") is None:
                        continue
                    f_market = float(row["mid"])
                    fwd_pts_cop = round(f_market - fx_spot, 4)
                    deval_ea = round(((f_market / fx_spot) ** (12 / months) - 1) * 100, 4)
                    ndf_payload[str(months)] = {
                        "fwd_pts_cop": fwd_pts_cop,
                        "F_market": round(f_market, 4),
                        "deval_ea": deval_ea,
                    }
                if not ndf_payload:
                    ndf_payload = recalc_ndf(last["ndf"], fx_spot)
                    fills.append("ndf")
            except Exception:
                ndf_payload = recalc_ndf(last["ndf"], fx_spot)
                fills.append("ndf")
        else:
            ndf_payload = recalc_ndf(last["ndf"], fx_spot)
            fills.append("ndf")

        # ── Display ──
        ibr_1d  = ibr_payload.get("ibr_1d", "N/A")
        ibr_12m = ibr_payload.get("ibr_12m", "N/A")
        fill_str = ",".join(fills) if fills else "all live"

        status = "DRY RUN" if dry_run else "STORED"
        print(f"{fecha:<12} {fx_spot:>10,.2f} {str(sofr_on_pct):>9} "
              f"{str(ibr_1d):>8} {str(ibr_12m):>9} {fill_str:>16}  {status}")

        row = {
            "fecha":   fecha,
            "fx_spot": fx_spot,
            "sofr_on": sofr_on_pct,
            "ibr":     ibr_payload,
            "sofr":    sofr_payload,
            "ndf":     ndf_payload,
        }

        # Update carry-forward
        last["fx_spot"] = fx_spot
        last["sofr_on"] = sofr_on_pct
        last["ibr"]     = ibr_payload
        last["sofr"]    = sofr_payload
        last["ndf"]     = ndf_payload

        if not dry_run:
            loader.store_marks(**row)

        stored += 1

    print()
    print("-" * 90)
    print(f"Existing: {skipped} | Filled: {stored}")
    if dry_run:
        print("Modo DRY RUN — no se guardo nada. Corre con --commit para guardar.")
    else:
        print("Backfill completado.")


if __name__ == "__main__":
    main()

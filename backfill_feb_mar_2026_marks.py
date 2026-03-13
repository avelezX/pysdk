"""
backfill_feb_mar_2026_marks.py — Backfill market_marks for Feb 26 – Mar 5, 2026

The compute_marks GitHub Actions workflow was created on Mar 3, 2026 and
then broke from Mar 4 onward due to a Python 3.9 / dict|None syntax error.
This script fills the gap for:
  - Feb 26–27 (before the workflow existed)
  - Mar 4–5   (workflow was crashing)

NDF forward points from cop_fwd_points may not be available for all dates,
so we fall back to the 2026-03-03 snapshot (the last complete mark).

Usage:
    python backfill_feb_mar_2026_marks.py            # dry run (preview only)
    python backfill_feb_mar_2026_marks.py --commit   # actually store to DB
"""
import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

import QuantLib as ql

from pricing.data.market_data import MarketDataLoader
from pricing.curves.curve_manager import CurveManager
from pricing.curves.ndf_curve import build_ndf_curve


# Last complete snapshot BEFORE the gap — used as carry-forward seed
CARRY_FORWARD_SEED = "2026-02-25"

# Date range to backfill
START_DATE = date(2026, 2, 26)
END_DATE   = date(2026, 3, 5)

# Dates to skip (weekends handled automatically)
SKIP_DATES: set[str] = set()


def recalc_ndf(ndf_snapshot: dict, fx_spot: float) -> dict:
    """Re-derive F_market and deval_ea from fwd_pts_cop using today's spot."""
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


def business_days(start: date, end: date) -> list[str]:
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += timedelta(days=1)
    return days


def build_ibr_payload(cm: CurveManager) -> dict:
    return {k: round(v, 6) for k, v in cm.status()["ibr"]["nodes"].items()}


def build_sofr_payload(cm: CurveManager) -> dict:
    tenors = [1, 3, 6, 12, 18, 24, 36, 60, 84, 120, 180, 240, 360, 480, 600]
    payload = {}
    for m in tenors:
        dt = cm.valuation_date + ql.Period(m, ql.Months)
        payload[str(m)] = round(cm.sofr_zero_rate(dt) * 100, 6)
    return payload


def main():
    commit = "--commit" in sys.argv
    force  = "--force" in sys.argv
    dry_run = not commit

    loader = MarketDataLoader()

    # ── Load last complete snapshot as carry-forward base ──
    # We use the most recent market_marks row before START_DATE as seed,
    # then Mar 3 as a second fallback.
    print(f"Loading carry-forward base from market_marks [{CARRY_FORWARD_SEED}]...")
    prev = loader.fetch_marks(target_date=CARRY_FORWARD_SEED)
    if prev is None:
        raise RuntimeError(f"No market_marks snapshot found for {CARRY_FORWARD_SEED}")

    # Carry-forward state: last known good values
    last = {
        "fx_spot":  prev["fx_spot"],
        "sofr_on":  prev["sofr_on"],
        "ibr":      prev["ibr"],
        "sofr":     prev["sofr"],
        "ndf":      prev["ndf"],
    }
    print(f"  Base fx_spot: {last['fx_spot']}")
    print(f"  Base IBR keys: {list(last['ibr'].keys())}")
    print(f"  Base SOFR keys: {list(last['sofr'].keys())}")
    print(f"  Base NDF keys: {list(last['ndf'].keys())}")
    print()

    # ── Check existing market_marks dates (skip already stored) ──
    existing = loader._get("market_marks", "select=fecha&order=fecha.asc")
    existing_dates = {row["fecha"] for row in existing}
    print(f"Already in market_marks: {sorted(d for d in existing_dates if d >= START_DATE.isoformat())}")
    print()

    bdays = business_days(START_DATE, END_DATE)
    results = []

    print(f"{'fecha':<12} {'fx_spot':>10} {'sofr_on':>9} {'ibr_1d':>8} {'ibr_12m':>9} {'fills':>12}  status")
    print("-" * 85)

    for fecha in bdays:
        if fecha in SKIP_DATES:
            print(f"{fecha:<12} {'---':>10} {'---':>9} {'---':>8} {'---':>9} {'---':>12}  SKIP (holiday)")
            continue
        if fecha in existing_dates and not force:
            print(f"{fecha:<12} {'---':>10} {'---':>9} {'---':>8} {'---':>9} {'---':>12}  SKIP (already stored)")
            continue

        fills = []  # track which fields used carry-forward

        # ── Fetch real market data for this date ──
        ibr_quotes = loader.fetch_ibr_quotes(target_date=fecha)
        sofr_df    = loader.fetch_sofr_curve(target_date=fecha)
        fx_spot    = loader.fetch_usdcop_spot(target_date=fecha)
        sofr_on    = loader.fetch_sofr_spot(target_date=fecha)

        # ── FX Spot: carry forward if missing ──
        if fx_spot is None:
            fx_spot = last["fx_spot"]
            fills.append("spot")

        # ── IBR: build if possible, else carry forward ──
        if ibr_quotes:
            try:
                cm = CurveManager()
                cm.build_ibr_curve(ibr_quotes)
                ibr_payload = build_ibr_payload(cm)
            except Exception:
                ibr_payload = last["ibr"]
                fills.append("ibr")
        else:
            ibr_payload = last["ibr"]
            fills.append("ibr")

        # ── SOFR curve: build if possible, else carry forward ──
        if not sofr_df.empty:
            try:
                if not ibr_quotes:
                    cm = CurveManager()
                cm.build_sofr_curve(sofr_df)
                cm.set_fx_spot(fx_spot)
                sofr_payload = build_sofr_payload(cm)
            except Exception:
                sofr_payload = last["sofr"]
                fills.append("sofr")
        else:
            sofr_payload = last["sofr"]
            fills.append("sofr")

        # ── SOFR ON: carry forward if missing ──
        sofr_on_pct = round(sofr_on * 100, 6) if sofr_on else None
        if sofr_on_pct is None:
            sofr_on_pct = last["sofr_on"]
            fills.append("on")

        # ── NDF: try real data first, fallback to carry forward ──
        # When carrying forward, only keep fwd_pts_cop (market data) and
        # recalculate F_market and deval_ea using today's spot.
        cop_fwd = loader.fetch_cop_forwards(target_date=fecha)
        if not cop_fwd.empty and hasattr(cm, 'sofr_handle') and cm.sofr_handle is not None:
            try:
                _, fwd_pts = build_ndf_curve(cop_fwd, fx_spot, cm.sofr_handle, cm.valuation_date)
                ndf_payload = {}
                for months, fwd_pts_cop in sorted(fwd_pts.items()):
                    f_market = fx_spot + fwd_pts_cop
                    deval_ea = round(((f_market / fx_spot) ** (12 / months) - 1) * 100, 4)
                    ndf_payload[str(months)] = {
                        "fwd_pts_cop": round(fwd_pts_cop, 4),
                        "F_market": round(f_market, 4),
                        "deval_ea": deval_ea,
                    }
            except Exception:
                ndf_payload = recalc_ndf(last["ndf"], fx_spot)
                fills.append("ndf")
        else:
            ndf_payload = recalc_ndf(last["ndf"], fx_spot)
            fills.append("ndf")

        ibr_1d  = ibr_payload.get("ibr_1d", "N/A")
        ibr_12m = ibr_payload.get("ibr_12m", "N/A")
        fill_str = ",".join(fills) if fills else "all live"

        status = "DRY RUN" if dry_run else "STORED"
        print(f"{fecha:<12} {fx_spot:>10,.2f} {str(sofr_on_pct):>9} "
              f"{str(ibr_1d):>8} {str(ibr_12m):>9} {fill_str:>12}  {status}")

        row = {
            "fecha":   fecha,
            "fx_spot": fx_spot,
            "sofr_on": sofr_on_pct,
            "ibr":     ibr_payload,
            "sofr":    sofr_payload,
            "ndf":     ndf_payload,
        }
        results.append(row)

        # Update carry-forward state with whatever we computed
        last["fx_spot"] = fx_spot
        last["sofr_on"] = sofr_on_pct
        last["ibr"]     = ibr_payload
        last["sofr"]    = sofr_payload
        last["ndf"]     = ndf_payload

        if not dry_run:
            loader.store_marks(**row)

    print()
    print("-" * 85)
    print(f"Total a insertar: {len(results)} fechas")
    if dry_run:
        print("Modo DRY RUN -- no se guardo nada. Corre con --commit para guardar.")
    else:
        print("Backfill completado.")


if __name__ == "__main__":
    main()

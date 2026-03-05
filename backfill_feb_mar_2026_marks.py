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


# Reference date for NDF fallback (last known good snapshot)
NDF_FALLBACK_DATE = "2026-03-03"

# Date range to backfill
START_DATE = date(2026, 2, 26)
END_DATE   = date(2026, 3, 5)

# Dates to skip (weekends handled automatically)
SKIP_DATES: set[str] = set()


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
    dry_run = not commit

    loader = MarketDataLoader()

    # ── Fetch fixed NDF fallback from the reference snapshot ──
    print(f"Fetching NDF fallback from market_marks [{NDF_FALLBACK_DATE}]...")
    ref = loader.fetch_marks(target_date=NDF_FALLBACK_DATE)
    if ref is None:
        raise RuntimeError(f"No market_marks snapshot found for {NDF_FALLBACK_DATE}")
    fixed_ndf = ref["ndf"]
    print(f"  NDF tenors: {list(fixed_ndf.keys())}")
    print()

    # ── Check existing market_marks dates (skip already stored) ──
    existing = loader._get("market_marks", "select=fecha&order=fecha.asc")
    existing_dates = {row["fecha"] for row in existing}
    print(f"Already in market_marks: {sorted(d for d in existing_dates if d >= START_DATE.isoformat())}")
    print()

    bdays = business_days(START_DATE, END_DATE)
    results = []

    print(f"{'fecha':<12} {'fx_spot':>10} {'sofr_on':>9} {'ibr_1d':>8} {'ibr_12m':>9} {'ndf_src':>9}  status")
    print("-" * 80)

    for fecha in bdays:
        if fecha in SKIP_DATES:
            print(f"{fecha:<12} {'—':>10} {'—':>9} {'—':>8} {'—':>9} {'—':>9}  SKIP (holiday)")
            continue
        if fecha in existing_dates:
            print(f"{fecha:<12} {'—':>10} {'—':>9} {'—':>8} {'—':>9} {'—':>9}  SKIP (already stored)")
            continue

        # ── Fetch real market data for this date ──
        ibr_quotes = loader.fetch_ibr_quotes(target_date=fecha)
        sofr_df    = loader.fetch_sofr_curve(target_date=fecha)
        fx_spot    = loader.fetch_usdcop_spot(target_date=fecha)
        sofr_on    = loader.fetch_sofr_spot(target_date=fecha)

        if not ibr_quotes or fx_spot is None:
            print(f"{fecha:<12} {'N/A':>10} {'N/A':>9} {'N/A':>8} {'N/A':>9} {'N/A':>9}  SKIP (missing data)")
            continue

        # ── Build curves ──
        cm = CurveManager()
        cm.build_ibr_curve(ibr_quotes)
        if not sofr_df.empty:
            cm.build_sofr_curve(sofr_df)
        cm.set_fx_spot(fx_spot)

        # ── NDF: try real data first, fallback to reference ──
        cop_fwd = loader.fetch_cop_forwards(target_date=fecha)
        ndf_src = "live"
        if not cop_fwd.empty and cm.sofr_handle is not None:
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
                ndf_payload = fixed_ndf
                ndf_src = "fallback"
        else:
            ndf_payload = fixed_ndf
            ndf_src = "fallback"

        ibr_payload  = build_ibr_payload(cm)
        sofr_payload = build_sofr_payload(cm) if not sofr_df.empty else {}
        sofr_on_pct  = round(sofr_on * 100, 6) if sofr_on else None

        ibr_1d  = ibr_payload.get("ibr_1d", "N/A")
        ibr_12m = ibr_payload.get("ibr_12m", "N/A")

        status = "DRY RUN" if dry_run else "STORED"
        print(f"{fecha:<12} {fx_spot:>10,.2f} {str(sofr_on_pct or 'N/A'):>9} "
              f"{str(ibr_1d):>8} {str(ibr_12m):>9} {ndf_src:>9}  {status}")

        results.append({
            "fecha":   fecha,
            "fx_spot": fx_spot,
            "sofr_on": sofr_on_pct,
            "ibr":     ibr_payload,
            "sofr":    sofr_payload,
            "ndf":     ndf_payload,
        })

        if not dry_run:
            loader.store_marks(
                fecha=fecha,
                fx_spot=fx_spot,
                sofr_on=sofr_on_pct,
                ibr=ibr_payload,
                sofr=sofr_payload,
                ndf=ndf_payload,
            )

    print()
    print("-" * 80)
    print(f"Total a insertar: {len(results)} fechas")
    if dry_run:
        print("Modo DRY RUN — no se guardó nada. Corre con --commit para guardar.")
    else:
        print("Backfill completado.")


if __name__ == "__main__":
    main()

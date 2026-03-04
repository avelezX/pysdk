"""
backfill_jan2026_marks.py — Backfill market_marks for January 2026

Uses real IBR, SOFR curve, FX spot, and SOFR ON for each business day,
but substitutes the NDF forward points from 2026-03-03 (first available
snapshot) since cop_fwd_points data doesn't exist for January 2026.

Usage:
    python backfill_jan2026_marks.py            # dry run (preview only)
    python backfill_jan2026_marks.py --commit   # actually store to DB
"""
import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

import QuantLib as ql

from pricing.data.market_data import MarketDataLoader
from pricing.curves.curve_manager import CurveManager


NDF_SOURCE_DATE = "2026-03-03"

# Jan 2026 weekdays to skip (no market data)
SKIP_DATES = {
    "2026-01-12",  # Colombian market holiday
    "2026-01-19",  # MLK Day (US) — no FX spot / SOFR ON
}


def jan2026_business_days() -> list[str]:
    days = []
    d = date(2026, 1, 1)
    while d <= date(2026, 1, 31):
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

    # ── Fetch fixed NDF from the reference snapshot ──
    print(f"Fetching fixed NDF from market_marks [{NDF_SOURCE_DATE}]...")
    ref = loader.fetch_marks(target_date=NDF_SOURCE_DATE)
    if ref is None:
        raise RuntimeError(f"No market_marks snapshot found for {NDF_SOURCE_DATE}")
    fixed_ndf = ref["ndf"]
    print(f"  NDF tenors: {list(fixed_ndf.keys())}")
    print()

    # ── Check existing market_marks dates (skip already stored) ──
    existing = loader._get("market_marks", "select=fecha&order=fecha.asc")
    existing_dates = {row["fecha"] for row in existing}
    print(f"Already in market_marks: {sorted(existing_dates)}")
    print()

    business_days = jan2026_business_days()
    results = []

    print(f"{'fecha':<12} {'fx_spot':>10} {'sofr_on':>9} {'ibr_1d':>8} {'ibr_12m':>9}  status")
    print("-" * 65)

    for fecha in business_days:
        if fecha in SKIP_DATES:
            print(f"{fecha:<12} {'—':>10} {'—':>9} {'—':>8} {'—':>9}  SKIP (no market data)")
            continue
        if fecha in existing_dates:
            print(f"{fecha:<12} {'—':>10} {'—':>9} {'—':>8} {'—':>9}  SKIP (already stored)")
            continue

        # ── Fetch real market data for this date ──
        ibr_quotes = loader.fetch_ibr_quotes(target_date=fecha)
        sofr_df    = loader.fetch_sofr_curve(target_date=fecha)
        fx_spot    = loader.fetch_usdcop_spot(target_date=fecha)
        sofr_on    = loader.fetch_sofr_spot(target_date=fecha)

        if not ibr_quotes or fx_spot is None:
            print(f"{fecha:<12} {'N/A':>10} {'N/A':>9} {'N/A':>8} {'N/A':>9}  SKIP (missing data)")
            continue

        # ── Build curves ──
        cm = CurveManager()
        cm.build_ibr_curve(ibr_quotes)
        if not sofr_df.empty:
            cm.build_sofr_curve(sofr_df)
        cm.set_fx_spot(fx_spot)

        ibr_payload  = build_ibr_payload(cm)
        sofr_payload = build_sofr_payload(cm) if not sofr_df.empty else {}
        sofr_on_pct  = round(sofr_on * 100, 6) if sofr_on else None

        ibr_1d  = ibr_payload.get("ibr_1d", "N/A")
        ibr_12m = ibr_payload.get("ibr_12m", "N/A")

        status = "DRY RUN" if dry_run else "STORED"
        print(f"{fecha:<12} {fx_spot:>10,.2f} {str(sofr_on_pct or 'N/A'):>9} "
              f"{str(ibr_1d):>8} {str(ibr_12m):>9}  {status}")

        results.append({
            "fecha":   fecha,
            "fx_spot": fx_spot,
            "sofr_on": sofr_on_pct,
            "ibr":     ibr_payload,
            "sofr":    sofr_payload,
            "ndf":     fixed_ndf,
        })

        if not dry_run:
            loader.store_marks(
                fecha=fecha,
                fx_spot=fx_spot,
                sofr_on=sofr_on_pct,
                ibr=ibr_payload,
                sofr=sofr_payload,
                ndf=fixed_ndf,
            )

    print()
    print("-" * 65)
    print(f"Total a insertar: {len(results)} fechas")
    if dry_run:
        print("Modo DRY RUN — no se guardó nada. Corre con --commit para guardar.")
    else:
        print("Backfill completado.")


if __name__ == "__main__":
    main()

"""
run_backfill_marks.py — Backfill missing market_marks using REST API only.

For each missing business day:
  - IBR:      fetched from BanRep via REST → QuantLib bootstrap
  - SOFR zeros: carried forward from last known market_marks row
  - FX spot:  fetched from currency_hour (SET-ICAP) via REST
  - SOFR ON:  fetched from us_reference_rates via REST
  - NDF:      carried forward fwd_pts_cop, F_market / deval_ea recomputed with actual spot

Usage:
    python run_backfill_marks.py               # dry run
    python run_backfill_marks.py --commit      # store to DB
    python run_backfill_marks.py --commit --from 2026-02-01   # start from specific date
"""
import sys
import os
from datetime import date, timedelta

import QuantLib as ql
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

from pricing.data.market_data import MarketDataLoader
from pricing.curves.curve_manager import CurveManager


START_DATE = date(2026, 1, 2)


def business_days(start: date, end: date) -> list[str]:
    days, d = [], start
    while d <= end:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += timedelta(days=1)
    return days


def recalc_ndf(ndf_snapshot: dict, fx_spot: float) -> dict:
    """Carry-forward: keep fwd_pts_cop, recompute F_market and deval_ea with new spot."""
    result = {}
    for months_str, v in ndf_snapshot.items():
        months = int(months_str)
        fwd_pts_cop = v["fwd_pts_cop"]
        f_market = fx_spot + fwd_pts_cop
        deval_ea = round(((f_market / fx_spot) ** (12 / months) - 1) * 100, 4)
        result[months_str] = {
            "fwd_pts_cop": round(fwd_pts_cop, 4),
            "F_market":    round(f_market, 4),
            "deval_ea":    deval_ea,
        }
    return result


def build_ibr_payload(cm: CurveManager) -> dict:
    return {k: round(v, 6) for k, v in cm.status()["ibr"]["nodes"].items()}


def main():
    commit  = "--commit" in sys.argv
    dry_run = not commit

    # Parse optional --from date
    start = START_DATE
    if "--from" in sys.argv:
        idx = sys.argv.index("--from")
        start = date.fromisoformat(sys.argv[idx + 1])

    loader = MarketDataLoader()

    # ── Load existing marks for carry-forward state ──
    existing_rows = loader._get("market_marks", "select=fecha,fx_spot,sofr_on,ibr,sofr,ndf&order=fecha.asc")
    existing_dates = {r["fecha"] for r in existing_rows}
    marks_by_date  = {r["fecha"]: r for r in existing_rows}

    bdays = business_days(start, date.today())
    gaps  = [d for d in bdays if d not in existing_dates]

    print(f"market_marks: {len(existing_dates)} existing | Business days since {start}: {len(bdays)} | Gaps: {len(gaps)}")
    if not gaps:
        print("No gaps to fill. Done.")
        return

    # ── Seed: last mark before the first gap ──
    # Find the latest existing mark that is <= start
    seed_candidates = sorted([d for d in existing_dates if d <= gaps[0]], reverse=True)
    if not seed_candidates:
        print("ERROR: No existing mark to seed from before the first gap.")
        return

    seed_date = seed_candidates[0]
    seed = marks_by_date[seed_date]
    last = {
        "fx_spot":  seed["fx_spot"],
        "sofr_on":  seed["sofr_on"],
        "ibr":      seed["ibr"],
        "sofr":     seed["sofr"],
        "ndf":      seed["ndf"],
    }
    print(f"Seed: {seed_date} (fx_spot={last['fx_spot']:,.2f})")
    print()
    print(f"{'fecha':<12} {'fx_spot':>10} {'sofr_on':>9} {'ibr_1d':>8} {'fills':>20}  status")
    print("-" * 80)

    stored = 0
    for fecha in bdays:
        # If this date already has a mark, update carry-forward state and move on
        if fecha in existing_dates:
            m = marks_by_date[fecha]
            last.update(fx_spot=m["fx_spot"], sofr_on=m["sofr_on"],
                        ibr=m["ibr"], sofr=m["sofr"], ndf=m["ndf"])
            continue

        fills = []

        # ── FX spot ──
        fx_spot = loader.fetch_usdcop_spot(target_date=fecha)
        if fx_spot is None:
            fx_spot = last["fx_spot"]
            fills.append("spot")

        # ── SOFR ON ──
        sofr_on_raw = loader.fetch_sofr_spot(target_date=fecha)
        sofr_on_pct = round(sofr_on_raw * 100, 6) if sofr_on_raw else None
        if sofr_on_pct is None:
            sofr_on_pct = last["sofr_on"]
            fills.append("on")

        # ── IBR: fetch quotes and bootstrap if available ──
        ibr_quotes = loader.fetch_ibr_quotes(target_date=fecha)
        cm = CurveManager()
        if ibr_quotes:
            try:
                cm.build_ibr_curve(ibr_quotes)
                ibr_payload = build_ibr_payload(cm)
            except Exception:
                ibr_payload = last["ibr"]
                fills.append("ibr")
        else:
            ibr_payload = last["ibr"]
            fills.append("ibr")

        # ── SOFR zeros: carry forward (sofr_swap_curve not accessible via REST) ──
        sofr_payload = last["sofr"]
        fills.append("sofr")

        # ── NDF: carry forward fwd_pts_cop, recompute with actual spot ──
        ndf_payload = recalc_ndf(last["ndf"], fx_spot)
        fills.append("ndf")

        # ── Print row ──
        ibr_1d   = ibr_payload.get("ibr_1d", "N/A")
        fill_str = ",".join(fills) if fills else "all live"
        status   = "DRY RUN" if dry_run else "STORED"
        print(f"{fecha:<12} {fx_spot:>10,.2f} {str(sofr_on_pct):>9} {str(ibr_1d):>8} {fill_str:>20}  {status}")

        # ── Update carry-forward state ──
        last.update(fx_spot=fx_spot, sofr_on=sofr_on_pct,
                    ibr=ibr_payload, sofr=sofr_payload, ndf=ndf_payload)

        if not dry_run:
            loader.store_marks(
                fecha=fecha,
                fx_spot=fx_spot,
                sofr_on=sofr_on_pct,
                ibr=ibr_payload,
                sofr=sofr_payload,
                ndf=ndf_payload,
            )

        stored += 1

    print()
    print("-" * 80)
    print(f"Gaps filled: {stored}")
    if dry_run:
        print("Modo DRY RUN — nada guardado. Corre con --commit para guardar.")
    else:
        print("Backfill completado.")


if __name__ == "__main__":
    main()

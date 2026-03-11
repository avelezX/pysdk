"""
run_compute_marks.py — Daily market marks snapshot

Computes all curves from the latest available data and stores one row
in market_marks (upsert by fecha). Intended to run daily at ~21:30 UTC,
after all collectors have finished (SOFR ~21:00, FXEmpire ~21:00).

Usage:
    python run_compute_marks.py             # uses today's date
    python run_compute_marks.py 2026-03-03  # specific date (backfill)

Output row in market_marks:
    fecha    | fx_spot | sofr_on | ibr (JSONB) | sofr (JSONB) | ndf (JSONB)
"""
import sys
import os
from datetime import date

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

import QuantLib as ql

from pricing.data.market_data import MarketDataLoader
from pricing.curves.curve_manager import CurveManager


def compute_marks(target_date: str = None) -> dict:
    """
    Fetch all market data, build curves, return structured marks dict.
    target_date: ISO string or None for latest available.
    """
    loader = MarketDataLoader()
    cm = CurveManager()

    # ── Fetch ──
    ibr_quotes = loader.fetch_ibr_quotes(target_date=target_date)
    sofr_df    = loader.fetch_sofr_curve(target_date=target_date)
    fx_spot    = loader.fetch_usdcop_spot(target_date=target_date)
    cop_fwd    = loader.fetch_cop_forwards(target_date=target_date)
    sofr_on    = loader.fetch_sofr_spot(target_date=target_date)

    if not ibr_quotes:
        raise RuntimeError("No IBR data available")
    if sofr_df.empty:
        raise RuntimeError("No SOFR data available")
    if fx_spot is None:
        raise RuntimeError("No FX spot available")
    if cop_fwd.empty:
        raise RuntimeError("No COP forward data available")

    # ── Build curves ──
    cm.build_ibr_curve(ibr_quotes)
    cm.build_sofr_curve(sofr_df)
    cm.set_fx_spot(fx_spot)

    # ── IBR nodes (% EA) ──
    ibr_payload = {k: round(v, 6) for k, v in cm.status()["ibr"]["nodes"].items()}

    # ── SOFR zero rates by tenor_months ──
    sofr_tenors = [1, 3, 6, 12, 18, 24, 36, 60, 84, 120, 180, 240, 360, 480, 600]
    sofr_payload = {}
    for m in sofr_tenors:
        dt = cm.valuation_date + ql.Period(m, ql.Months)
        sofr_payload[str(m)] = round(cm.sofr_zero_rate(dt) * 100, 6)

    # ── NDF forwards by tenor_months ──
    # Use mid (outright forward) directly from cop_fwd_points — no SOFR bootstrap needed.
    # mid IS the market-observed outright forward (e.g. 3,775.69 for 1M).
    # fwd_pts_cop = mid - fx_spot anchors the differential to the SET-ICAP spot.
    ndf_payload = {}
    for _, row in cop_fwd.iterrows():
        months = int(row["tenor_months"])
        if months <= 0 or row.get("mid") is None:
            continue
        f_market = float(row["mid"])
        fwd_pts_cop = round(f_market - fx_spot, 4)
        deval_ea = round(((f_market / fx_spot) ** (12 / months) - 1) * 100, 4)
        ndf_payload[str(months)] = {
            "fwd_pts_cop": fwd_pts_cop,
            "F_market":    round(f_market, 4),
            "deval_ea":    deval_ea,
        }

    return {
        "ibr_quotes":  ibr_quotes,   # kept for fecha inference
        "fx_spot":     fx_spot,
        "sofr_on":     round(sofr_on * 100, 6) if sofr_on else None,
        "ibr":         ibr_payload,
        "sofr":        sofr_payload,
        "ndf":         ndf_payload,
        "loader":      loader,
        "target_date": target_date,
        "sofr_df":     sofr_df,
        "cop_fwd":     cop_fwd,
    }


def infer_fecha(marks: dict) -> str:
    """
    Determine the trading date for this marks snapshot.

    When running live (target_date=None) we always use today — individual
    data sources may have slightly different dates (e.g. SOFR closes at
    21:00 UTC so it may be yesterday's) but the snapshot represents today's
    mark set. For backfill runs, use the explicit target_date.
    """
    return marks["target_date"] or date.today().isoformat()


def main():
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"run_compute_marks — {date.today().isoformat()}")
    print(f"  target_date: {target_date or 'latest available'}")
    print()

    # ── Compute ──
    print("  Computing curves...")
    marks = compute_marks(target_date)
    fecha = infer_fecha(marks)
    print(f"  Fecha marcas: {fecha}")
    print(f"  FX spot:      {marks['fx_spot']:,.2f} COP/USD")
    print(f"  SOFR ON:      {marks['sofr_on']:.4f}%" if marks["sofr_on"] else "  SOFR ON:      N/A")
    print(f"  IBR nodes:    {len(marks['ibr'])}")
    print(f"  SOFR tenores: {len(marks['sofr'])}")
    print(f"  NDF tenores:  {len(marks['ndf'])}")
    print()

    # ── Store ──
    print("  Storing to market_marks...")
    loader = marks["loader"]
    loader.store_marks(
        fecha=fecha,
        fx_spot=marks["fx_spot"],
        sofr_on=marks["sofr_on"],
        ibr=marks["ibr"],
        sofr=marks["sofr"],
        ndf=marks["ndf"],
    )
    print(f"  Stored OK — fecha={fecha}")
    print()
    print("Done!")


if __name__ == "__main__":
    main()

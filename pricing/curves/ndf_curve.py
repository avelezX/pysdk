"""
NDF-implied COP discount curve builder.

Bootstraps a COP discount curve from market-observed USD/COP forward rates.
This captures the NDF market basis (credit, convertibility risk, supply/demand)
that interest rate parity misses.

From interest rate parity:
  F(T) = Spot × DF_USD(T) / DF_COP(T)

Given market forwards F(T), spot S, and the SOFR curve (DF_USD), we solve:
  DF_COP(T) = Spot × DF_USD(T) / F(T)

These discount factors are assembled into a ql.DiscountCurve with
log-linear interpolation.

This curve should be used for NDF pricing instead of the IBR curve.
The IBR curve remains correct for IBR swaps.

Data source: cop_fwd_points table (FXEmpire collector)
  - Tenors: 1M through 10Y (market-observed outright forwards)
  - mid column: outright USD/COP forward (e.g. 3,775.69 for 1M) — used directly.
  - fwd_pts_cop = mid - spot (SET-ICAP) anchors the differential to the
    authoritative Colombian interbank fixing.
"""
import QuantLib as ql
import pandas as pd
from utilities.colombia_calendar import calendar_colombia


def build_ndf_curve(
    cop_fwd_df: pd.DataFrame,
    spot: float,
    sofr_handle: ql.YieldTermStructureHandle,
    valuation_date: ql.Date = None,
) -> tuple[ql.YieldTermStructure, dict]:
    """
    Build NDF-implied COP discount curve from market forwards.

    Computes DF_COP(T) = Spot * DF_USD(T) / F_market(T) for each tenor,
    then constructs a ql.DiscountCurve.

    Args:
        cop_fwd_df: DataFrame from cop_fwd_points with columns:
                    tenor, tenor_months, fwd_points
        spot: USD/COP spot rate from SET-ICAP (currency_hour table)
        sofr_handle: YieldTermStructureHandle linked to SOFR curve
        valuation_date: QL valuation date

    Returns:
        (curve, fwd_points_dict)
        - curve: DiscountCurve (NDF-implied COP curve)
        - fwd_points_dict: {tenor_months: forward_points} for display/overrides
    """
    if valuation_date is not None:
        ql.Settings.instance().evaluationDate = valuation_date
    else:
        valuation_date = ql.Settings.instance().evaluationDate

    calendar = ql.JointCalendar(
        calendar_colombia(),
        ql.UnitedStates(ql.UnitedStates.FederalReserve),
    )

    dates = [valuation_date]
    dfs = [1.0]
    fwd_points = {}

    for _, row in cop_fwd_df.iterrows():
        months = int(row["tenor_months"])
        if months <= 0:
            continue

        mat = calendar.advance(
            valuation_date, ql.Period(months, ql.Months), ql.Following
        )
        # Use mid (outright forward) directly — the market-observed USD/COP rate.
        # mid is already the full outright (e.g. 3,775.69 for 1M), no reconstruction needed.
        fwd_market = float(row["mid"])
        df_usd = sofr_handle.discount(mat)

        # Core formula: DF_COP = Spot * DF_USD / Forward
        df_cop = spot * df_usd / fwd_market

        dates.append(mat)
        dfs.append(df_cop)
        fwd_points[months] = round(fwd_market - spot, 2)

    curve = ql.DiscountCurve(dates, dfs, ql.Actual360())
    curve.enableExtrapolation()

    return curve, fwd_points

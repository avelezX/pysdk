"""
SOFR OIS curve builder using QuantLib.

Conventions:
  - Index: SOFR (OvernightIndex), USD currency, Actual360
  - Calendar: UnitedStates(FederalReserve)
  - Settlement: T+2
  - Fixed leg: Annual, ModifiedFollowing, Actual360
  - Interpolation: PiecewiseLogLinearDiscount

Data source: sofr_swap_curve table (Eris Futures par coupon rates)
  - 22 tenors: 1M through 50Y
  - swap_rate is in percent (e.g., 4.25 means 4.25%)

Each tenor rate is stored as a ql.SimpleQuote so it can be modified
for scenario analysis without rebuilding the curve.
"""
import QuantLib as ql
import pandas as pd


# ── SOFR Convention Details (analogous to ibr_quantlib_det) ──
sofr_quantlib_det = {
    "name": "SOFR",
    "fixingDays": 0,
    "currency": ql.USDCurrency(),
    "end_of_month": False,
    "calendar": ql.UnitedStates(ql.UnitedStates.FederalReserve),
    "business_convention": ql.ModifiedFollowing,
    "dayCounter": ql.Actual360(),
    "settlement_days": 2,
}


def _months_to_period(months: int) -> ql.Period:
    """Convert months integer to ql.Period."""
    if months < 12:
        return ql.Period(months, ql.Months)
    years = months // 12
    remainder = months % 12
    if remainder == 0:
        return ql.Period(years, ql.Years)
    return ql.Period(months, ql.Months)


def _build_helpers_with_quotes(df: pd.DataFrame) -> tuple[list, dict]:
    """
    Build rate helpers from SOFR swap curve DataFrame.
    Each rate is wrapped in a SimpleQuote for later modification.

    Args:
        df: DataFrame with columns: tenor_months, swap_rate (in percent)

    Returns:
        (helpers, quotes_dict)
        - helpers: list of ql.RateHelper
        - quotes_dict: {tenor_months: ql.SimpleQuote} for node overrides
    """
    helpers = []
    quotes = {}

    for _, row in df.iterrows():
        tenor_months = int(row["tenor_months"])
        rate_pct = float(row["swap_rate"])
        rate_decimal = rate_pct / 100.0

        sq = ql.SimpleQuote(rate_decimal)
        handle = ql.QuoteHandle(sq)
        quotes[tenor_months] = sq

        period = _months_to_period(tenor_months)

        if tenor_months <= 12:
            helper = ql.DepositRateHelper(
                handle,
                period,
                sofr_quantlib_det["settlement_days"],
                sofr_quantlib_det["calendar"],
                sofr_quantlib_det["business_convention"],
                sofr_quantlib_det["end_of_month"],
                sofr_quantlib_det["dayCounter"],
            )
        else:
            helper = ql.OISRateHelper(
                sofr_quantlib_det["settlement_days"],
                period,
                handle,
                ql.OvernightIndex(
                    "SOFR",
                    sofr_quantlib_det["fixingDays"],
                    sofr_quantlib_det["currency"],
                    sofr_quantlib_det["calendar"],
                    sofr_quantlib_det["dayCounter"],
                ),
            )

        helpers.append(helper)

    return helpers, quotes


def build_sofr_curve(
    df: pd.DataFrame, valuation_date: ql.Date = None
) -> tuple[ql.YieldTermStructure, dict]:
    """
    Build the SOFR discount curve from par swap rate data.

    Args:
        df: DataFrame with columns: tenor_months, swap_rate (in percent)
        valuation_date: QL valuation date. Defaults to today.

    Returns:
        (curve, quotes_dict)
        - curve: PiecewiseLogLinearDiscount
        - quotes_dict: {tenor_months: SimpleQuote} for node modifications
    """
    if valuation_date is not None:
        ql.Settings.instance().evaluationDate = valuation_date

    helpers, quotes = _build_helpers_with_quotes(df)

    curve = ql.PiecewiseLogLinearDiscount(
        sofr_quantlib_det["settlement_days"],
        sofr_quantlib_det["calendar"],
        helpers,
        sofr_quantlib_det["dayCounter"],
    )
    curve.enableExtrapolation()

    return curve, quotes

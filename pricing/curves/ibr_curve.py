"""
IBR OIS curve builder.
Wraps existing swap_functions logic, adding SimpleQuote-based node overrides.

Conventions (from swap_functions/ibr_quantlib_details.py):
  - Index: IBR1D (OvernightIndex), COP currency, Actual360
  - Calendar: Colombia (utilities/colombia_calendar.py)
  - Settlement: T+2 (fixingDays=1 on the index)
  - Fixed leg: Quarterly, Following, Actual360
  - Interpolation: PiecewiseLogLinearDiscount

Data source: ibr_swaps_cluster table
  - Tenors: 1D, 1M, 3M, 6M, 12M (deposits), 2Y-20Y (OIS swaps)
  - Rates in percent (e.g., 9.50 means 9.50%)

Each tenor rate is stored as a ql.SimpleQuote for scenario analysis.
"""
import QuantLib as ql
from utilities.colombia_calendar import calendar_colombia
from swap_functions.ibr_quantlib_details import ibr_quantlib_det, ibr_overnight_index

# Re-export for convenience
IBR_DETAILS = ibr_quantlib_det
IBR_INDEX = ibr_overnight_index

# Tenor definitions: (dict_key, ql_tenor, ql_unit, is_swap)
_TENOR_DEFS = [
    ("ibr_1d", 1, ql.Days, False),
    ("ibr_1m", 1, ql.Months, False),
    ("ibr_3m", 3, ql.Months, False),
    ("ibr_6m", 6, ql.Months, False),
    ("ibr_12m", 12, ql.Months, False),
    ("ibr_2y", 24, ql.Months, True),
    ("ibr_5y", 60, ql.Months, True),
    ("ibr_10y", 120, ql.Months, True),
    ("ibr_15y", 180, ql.Months, True),
    ("ibr_20y", 240, ql.Months, True),
]


def _build_helpers_with_quotes(db_info: dict) -> tuple[list, dict]:
    """
    Build IBR rate helpers from db_info dict, each backed by a SimpleQuote.

    Args:
        db_info: Dict with keys like ibr_1d, ibr_1m, ..., ibr_20y.
                 Values are lists where [0] is the rate in percent.

    Returns:
        (helpers, quotes_dict)
        - helpers: list of ql.RateHelper
        - quotes_dict: {tenor_key: SimpleQuote} for node overrides
    """
    helpers = []
    quotes = {}
    cal = ibr_quantlib_det["calendar"]

    for key, tenor, unit, is_swap in _TENOR_DEFS:
        if key not in db_info or db_info[key][0] is None:
            continue

        rate_decimal = db_info[key][0] / 100.0
        sq = ql.SimpleQuote(rate_decimal)
        handle = ql.QuoteHandle(sq)
        quotes[key] = sq

        if is_swap:
            helper = ql.SwapRateHelper(
                handle,
                ql.Period(tenor, unit),
                cal,
                ql.Quarterly,
                ibr_quantlib_det["bussiness_convention"],
                ibr_quantlib_det["dayCounter"],
                ibr_overnight_index,
            )
        else:
            helper = ql.DepositRateHelper(
                handle,
                ql.Period(tenor, unit),
                ibr_quantlib_det["settlement_days"],
                cal,
                ibr_quantlib_det["bussiness_convention"],
                ibr_quantlib_det["end_of_month"],
                ibr_quantlib_det["dayCounter"],
            )

        helpers.append(helper)

    return helpers, quotes


def build_ibr_curve(
    db_info: dict, valuation_date: ql.Date = None
) -> tuple[ql.YieldTermStructure, dict]:
    """
    Build the IBR discount curve from quote dictionary.

    Args:
        db_info: Dict with IBR quotes (percent, list format).
        valuation_date: QL valuation date.

    Returns:
        (curve, quotes_dict)
        - curve: PiecewiseLogLinearDiscount
        - quotes_dict: {tenor_key: SimpleQuote} for node modifications
    """
    if valuation_date is not None:
        ql.Settings.instance().evaluationDate = valuation_date

    helpers, quotes = _build_helpers_with_quotes(db_info)

    curve = ql.PiecewiseLogLinearDiscount(
        0,
        ibr_quantlib_det["calendar"],
        helpers,
        ql.Actual360(),
    )
    curve.enableExtrapolation()

    return curve, quotes

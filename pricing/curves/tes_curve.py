"""
TES bond yield curve builder.
Wraps existing bond_functions logic.

Conventions (from bond_functions/tes_quant_lib_details.py):
  - Day count: Actual36525
  - Business convention: Unadjusted
  - Coupon frequency: Annual
  - Calendar: Colombia
  - Settlement days: 0
  - Face amount: 100
  - Interpolation: PiecewiseLogCubicDiscount

Data source: tes table (bond master data) + market prices
"""
import QuantLib as ql
import pandas as pd
from bond_functions.tes_quant_lib_details import tes_quantlib_det
from bond_functions.bond_curve_structures import BondCurve
from utilities.date_functions import datetime_to_ql

TES_DETAILS = tes_quantlib_det


def build_tes_curve(
    bond_info_df: pd.DataFrame,
    market_prices_df: pd.DataFrame,
    valuation_date: ql.Date = None,
    currency: str = "COP",
    excluded_bonds: list = None,
) -> ql.YieldTermStructure:
    """
    Build TES yield curve from bond info and market prices.

    Args:
        bond_info_df: DataFrame with columns: name, emision, maduracion, cupon, moneda
        market_prices_df: DataFrame with columns matching BondCurve.create_bond_helpers
                         (needs 'close', 'maturity' columns indexed by bond name)
        valuation_date: QL valuation date
        currency: Filter bonds by currency ('COP' or 'UVR')
        excluded_bonds: List of bond names to exclude

    Returns:
        PiecewiseLogCubicDiscount curve
    """
    if valuation_date is not None:
        ql.Settings.instance().evaluationDate = valuation_date
        details = dict(tes_quantlib_det)
        details["calc_date"] = valuation_date
    else:
        details = tes_quantlib_det

    bc = BondCurve(currency=currency, bond_info_df=bond_info_df, bond_ql_details=details)
    bond_helpers = bc.create_bond_helpers(
        cop_df=market_prices_df, excluded_bonds=excluded_bonds or []
    )

    calc_date = valuation_date or ql.Date.todaysDate()
    curve = bc.yield_curve_ql(calc_date, bond_helpers=bond_helpers)
    curve.enableExtrapolation()

    return curve

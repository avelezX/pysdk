"""
TES Bond pricer with full analytics.

Enhances the existing bond_structure.py with:
  - DiscountingBondEngine linked to the TES yield curve handle
  - Clean price, dirty price, accrued interest
  - Yield to maturity (YTM)
  - Duration (Macaulay and Modified)
  - Convexity, DV01, BPV
"""
import QuantLib as ql
import pandas as pd
from datetime import datetime
from utilities.date_functions import datetime_to_ql, ql_to_datetime
from utilities.colombia_calendar import calendar_colombia
from bond_functions.tes_quant_lib_details import tes_quantlib_det


class TesBondPricer:
    """
    Prices individual TES bonds using the TES yield curve from CurveManager.
    """

    def __init__(self, curve_manager):
        self.cm = curve_manager
        self.calendar = calendar_colombia()
        self.details = tes_quantlib_det

    def create_bond(
        self,
        issue_date,
        maturity_date,
        coupon_rate: float,
        face_value: float = 100.0,
    ) -> ql.FixedRateBond:
        """
        Create a QuantLib FixedRateBond for a TES bond.

        Args:
            issue_date: Bond issuance date (datetime or ql.Date)
            maturity_date: Bond maturity date (datetime or ql.Date)
            coupon_rate: Annual coupon rate as decimal (e.g., 0.07)
            face_value: Face/par value (default 100)

        Returns:
            ql.FixedRateBond with pricing engine set
        """
        if isinstance(issue_date, datetime):
            issue_date = datetime_to_ql(issue_date)
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        schedule = ql.Schedule(
            issue_date, maturity_date,
            ql.Period(ql.Annual),
            self.calendar,
            ql.Unadjusted, ql.Unadjusted,
            ql.DateGeneration.Backward,
            True,
        )

        bond = ql.FixedRateBond(
            0,
            face_value,
            schedule,
            [coupon_rate],
            ql.Actual36525(),
            ql.Unadjusted,
        )

        engine = ql.DiscountingBondEngine(self.cm.tes_handle)
        bond.setPricingEngine(engine)

        return bond

    def analytics(
        self,
        issue_date,
        maturity_date,
        coupon_rate: float,
        market_clean_price: float = None,
        face_value: float = 100.0,
    ) -> dict:
        """
        Compute full analytics for a TES bond.

        Args:
            issue_date: Bond issuance date
            maturity_date: Bond maturity date
            coupon_rate: Annual coupon rate as decimal
            market_clean_price: If provided, used to compute YTM.
            face_value: Face value

        Returns:
            dict with all analytics
        """
        bond = self.create_bond(issue_date, maturity_date, coupon_rate, face_value)

        clean_price = bond.cleanPrice()
        dirty_price = bond.dirtyPrice()
        accrued = bond.accruedAmount()
        npv = bond.NPV()

        if market_clean_price is not None:
            ytm = bond.bondYield(
                market_clean_price, ql.Actual36525(), ql.Compounded, ql.Annual
            )
            price_for_risk = market_clean_price
        else:
            ytm = bond.bondYield(
                clean_price, ql.Actual36525(), ql.Compounded, ql.Annual
            )
            price_for_risk = clean_price

        flat_rate = ql.InterestRate(ytm, ql.Actual36525(), ql.Compounded, ql.Annual)

        macaulay_dur = ql.BondFunctions.duration(bond, flat_rate, ql.Duration.Macaulay)
        modified_dur = ql.BondFunctions.duration(bond, flat_rate, ql.Duration.Modified)
        convexity = ql.BondFunctions.convexity(bond, flat_rate)

        dirty_for_risk = price_for_risk + accrued
        dv01 = modified_dur * dirty_for_risk / 10000.0
        bpv = dv01 * face_value / 100.0

        mat_dt = ql_to_datetime(maturity_date) if isinstance(maturity_date, ql.Date) else maturity_date

        return {
            "clean_price": clean_price,
            "dirty_price": dirty_price,
            "accrued_interest": accrued,
            "npv": npv,
            "ytm": ytm,
            "macaulay_duration": macaulay_dur,
            "modified_duration": modified_dur,
            "convexity": convexity,
            "dv01": dv01,
            "bpv": bpv,
            "coupon_rate": coupon_rate,
            "face_value": face_value,
            "maturity": mat_dt,
        }

    def price_portfolio(self, bonds_df: pd.DataFrame) -> pd.DataFrame:
        """
        Price a portfolio of TES bonds.

        Args:
            bonds_df: DataFrame with columns: name, emision, maduracion, cupon,
                      notional (optional), market_price (optional)

        Returns:
            DataFrame with all analytics per bond
        """
        results = []
        for _, row in bonds_df.iterrows():
            notional = row.get("notional", 100.0)
            market_price = row.get("market_price", None)

            analytics = self.analytics(
                issue_date=row["emision"],
                maturity_date=row["maduracion"],
                coupon_rate=row["cupon"],
                market_clean_price=market_price,
                face_value=notional,
            )
            analytics["name"] = row["name"]
            results.append(analytics)

        return pd.DataFrame(results)

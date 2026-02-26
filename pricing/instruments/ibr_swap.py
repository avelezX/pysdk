"""
IBR Overnight Indexed Swap pricer.

Structure:
  - Fixed leg: Quarterly payments, Actual360, Following, Colombia calendar
  - Floating leg: IBR overnight compounded, Actual360

Conventions match swap_functions/ibr_quantlib_details.py:
  fixedLegFrequency = Quarterly
  fixedLegConvention = Following
  fixedLegDayCounter = Actual360()
"""
import QuantLib as ql
import pandas as pd
from datetime import datetime
from utilities.date_functions import datetime_to_ql, ql_to_datetime
from utilities.colombia_calendar import calendar_colombia


class IbrSwapPricer:
    """
    Prices IBR OIS swaps (fixed vs floating IBR overnight).
    Uses ql.OvernightIndexedSwap for native QuantLib pricing.
    """

    def __init__(self, curve_manager):
        self.cm = curve_manager
        self.calendar = calendar_colombia()

    def create_swap(
        self,
        notional: float,
        tenor_or_maturity,
        fixed_rate: float,
        pay_fixed: bool = True,
        spread: float = 0.0,
    ) -> ql.OvernightIndexedSwap:
        """
        Create an IBR OIS swap.

        Args:
            notional: COP notional amount
            tenor_or_maturity: ql.Period (e.g., ql.Period(5, ql.Years))
                              or ql.Date/datetime for maturity
            fixed_rate: Fixed leg rate as decimal (e.g., 0.0950)
            pay_fixed: True = pay fixed / receive floating
            spread: Spread over IBR floating leg (decimal)

        Returns:
            ql.OvernightIndexedSwap with pricing engine set
        """
        swap_type = (
            ql.OvernightIndexedSwap.Payer
            if pay_fixed
            else ql.OvernightIndexedSwap.Receiver
        )

        if isinstance(tenor_or_maturity, datetime):
            tenor_or_maturity = datetime_to_ql(tenor_or_maturity)

        if isinstance(tenor_or_maturity, ql.Period):
            start_date = self.calendar.advance(self.cm.valuation_date, 2, ql.Days)
            maturity_date = self.calendar.advance(start_date, tenor_or_maturity)
        else:
            start_date = self.calendar.advance(self.cm.valuation_date, 2, ql.Days)
            maturity_date = tenor_or_maturity

        schedule = ql.Schedule(
            start_date, maturity_date,
            ql.Period(ql.Quarterly),
            self.calendar,
            ql.Following, ql.Following,
            ql.DateGeneration.Forward, False,
        )

        swap = ql.OvernightIndexedSwap(
            swap_type,
            notional,
            schedule,
            fixed_rate,
            ql.Actual360(),
            self.cm.ibr_index,
            spread,
        )

        engine = ql.DiscountingSwapEngine(self.cm.ibr_handle)
        swap.setPricingEngine(engine)

        return swap

    def price(
        self,
        notional: float,
        tenor_or_maturity,
        fixed_rate: float,
        pay_fixed: bool = True,
        spread: float = 0.0,
    ) -> dict:
        """
        Price an IBR OIS swap and return analytics.

        Returns:
            dict with: npv, fair_rate, fixed_leg_npv, floating_leg_npv,
                      fixed_leg_bps, dv01, notional
        """
        swap = self.create_swap(notional, tenor_or_maturity, fixed_rate, pay_fixed, spread)

        npv = swap.NPV()
        fair_rate = swap.fairRate()
        fixed_leg_npv = swap.fixedLegNPV()
        floating_leg_npv = swap.overnightLegNPV()
        fixed_leg_bps = swap.fixedLegBPS()

        # Carry: current period's IBR forward rate vs fixed rate
        day_counter = ql.Actual360()
        ref_date = self.cm.ibr_handle.referenceDate()
        # Get 3M forward IBR rate from today
        fwd_end = self.calendar.advance(ref_date, ql.Period(3, ql.Months))
        ibr_fwd = self.cm.ibr_handle.forwardRate(
            ref_date, fwd_end, day_counter, ql.Simple
        ).rate()
        tau = day_counter.yearFraction(ref_date, fwd_end)
        sign = 1.0 if pay_fixed else -1.0
        # pay_fixed: I pay fixed, receive floating → carry positive when IBR > fixed
        carry_cop = sign * (ibr_fwd + spread - fixed_rate) * notional * tau
        carry_differential_bps = round((ibr_fwd + spread - fixed_rate) * 10000, 1)

        return {
            "npv": npv,
            "fair_rate": fair_rate,
            "fixed_rate": fixed_rate,
            "fixed_leg_npv": fixed_leg_npv,
            "floating_leg_npv": floating_leg_npv,
            "fixed_leg_bps": fixed_leg_bps,
            "dv01": abs(fixed_leg_bps),
            "notional": notional,
            "pay_fixed": pay_fixed,
            "spread": spread,
            "carry_cop": round(carry_cop, 2),
            "carry_rate_floating_pct": round(ibr_fwd * 100, 4),
            "carry_rate_fixed_pct": round(fixed_rate * 100, 4),
            "carry_differential_bps": carry_differential_bps,
        }

    def par_rate(self, tenor: ql.Period) -> float:
        """
        Compute the par swap rate for a given tenor.

        Args:
            tenor: e.g., ql.Period(5, ql.Years)

        Returns:
            Par fixed rate as decimal
        """
        swap = self.create_swap(
            notional=1_000_000_000,
            tenor_or_maturity=tenor,
            fixed_rate=0.05,
            pay_fixed=True,
        )
        return swap.fairRate()

    def par_curve(self, tenors: list = None) -> pd.DataFrame:
        """
        Build a par swap rate curve for standard tenors.

        Args:
            tenors: List of (label, ql.Period) tuples.

        Returns:
            DataFrame with: tenor, tenor_years, par_rate
        """
        if tenors is None:
            tenors = [
                ("1Y", ql.Period(1, ql.Years)),
                ("2Y", ql.Period(2, ql.Years)),
                ("3Y", ql.Period(3, ql.Years)),
                ("5Y", ql.Period(5, ql.Years)),
                ("7Y", ql.Period(7, ql.Years)),
                ("10Y", ql.Period(10, ql.Years)),
                ("15Y", ql.Period(15, ql.Years)),
                ("20Y", ql.Period(20, ql.Years)),
            ]

        results = []
        for label, period in tenors:
            try:
                rate = self.par_rate(period)
                results.append({
                    "tenor": label,
                    "tenor_years": period.length() if period.units() == ql.Years else period.length() / 12,
                    "par_rate": rate,
                })
            except Exception as e:
                results.append({
                    "tenor": label,
                    "par_rate": None,
                    "error": str(e),
                })

        return pd.DataFrame(results)

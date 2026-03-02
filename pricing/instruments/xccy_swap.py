"""
USD/COP Cross-Currency Swap pricer.

Structure:
  - COP leg: Floating IBR overnight (compounded) + xccy basis spread
  - USD leg: Floating SOFR overnight (compounded)
  - Notional exchange at start and end (at initial FX rate)

Pricing uses dual-curve discounting:
  - COP cashflows discounted with IBR curve
  - USD cashflows discounted with SOFR curve
  - All values converted to common currency (COP) at FX spot

Note: QuantLib Python bindings don't expose a native CrossCurrencyBasisSwap.
This implementation manually computes each leg's PV using forward rates
and discount factors — standard practice in production systems.
"""
import QuantLib as ql
import pandas as pd
from datetime import datetime
from scipy.optimize import brentq
from utilities.date_functions import datetime_to_ql, ql_to_datetime


class XccySwapPricer:
    """
    Prices COP/USD Cross-Currency basis swaps.
    Requires CurveManager with IBR and SOFR curves, plus FX spot.
    """

    def __init__(self, curve_manager):
        self.cm = curve_manager

    def price(
        self,
        notional_usd: float,
        start_date,
        maturity_date,
        xccy_basis_bps: float = 0.0,
        pay_usd: bool = True,
        fx_initial: float = None,
        cop_spread_bps: float = 0.0,
        usd_spread_bps: float = 0.0,
        payment_frequency: ql.Period = ql.Period(3, ql.Months),
    ) -> dict:
        """
        Price a cross-currency swap.

        Structure: Pay USD SOFR flat / Receive COP IBR + xccy_basis
                   (or reverse if pay_usd=False)

        Args:
            notional_usd: USD notional amount
            start_date: Swap start date (datetime or ql.Date)
            maturity_date: Swap maturity date
            xccy_basis_bps: Cross-currency basis spread in bps (added to COP leg)
            pay_usd: If True, we pay USD and receive COP
            fx_initial: FX rate at inception for notional exchange
            cop_spread_bps: Additional spread on COP leg (bps)
            usd_spread_bps: Additional spread on USD leg (bps)
            payment_frequency: Payment frequency for both legs

        Returns:
            dict with NPV, leg values, par basis spread
        """
        if isinstance(start_date, datetime):
            start_date = datetime_to_ql(start_date)
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        fx = fx_initial or self.cm.fx_spot
        notional_cop = notional_usd * fx

        # Joint calendar for schedule
        cop_cal = self.cm.ibr_index.fixingCalendar()
        usd_cal = self.cm.sofr_index.fixingCalendar()
        joint_cal = ql.JointCalendar(cop_cal, usd_cal)

        eval_date = ql.Settings.instance().evaluationDate
        is_midlife = start_date < eval_date

        # For mid-life swaps, build schedule from evaluation_date to avoid
        # QuantLib "negative time" errors when discounting past dates.
        schedule_start = eval_date if is_midlife else start_date
        schedule = ql.Schedule(
            schedule_start, maturity_date,
            payment_frequency,
            joint_cal,
            ql.ModifiedFollowing, ql.ModifiedFollowing,
            ql.DateGeneration.Forward, False,
        )

        # USD Leg (SOFR floating)
        usd_leg_value = self._value_ois_leg(
            schedule, notional_usd,
            self.cm.sofr_handle,
            usd_spread_bps / 10000.0,
            ql.Actual360(),
        )

        # COP Leg (IBR floating + xccy basis)
        total_cop_spread = (xccy_basis_bps + cop_spread_bps) / 10000.0
        cop_leg_value = self._value_ois_leg(
            schedule, notional_cop,
            self.cm.ibr_handle,
            total_cop_spread,
            ql.Actual360(),
        )

        # Notional exchange PV
        # Initial exchange: already settled for mid-life swaps, so PV = 0.
        # Only the final re-exchange at maturity remains.
        if is_midlife:
            usd_notional_pv = notional_usd * self.cm.sofr_handle.discount(maturity_date)
            cop_notional_pv = -notional_cop * self.cm.ibr_handle.discount(maturity_date)
        else:
            usd_notional_pv = (
                -notional_usd * self.cm.sofr_handle.discount(start_date)
                + notional_usd * self.cm.sofr_handle.discount(maturity_date)
            )
            cop_notional_pv = (
                notional_cop * self.cm.ibr_handle.discount(start_date)
                - notional_cop * self.cm.ibr_handle.discount(maturity_date)
            )

        usd_total = usd_leg_value + usd_notional_pv
        cop_total = cop_leg_value + cop_notional_pv

        spot = self.cm.fx_spot
        sign = 1.0 if pay_usd else -1.0
        npv_cop = sign * (-usd_total * spot + cop_total)
        npv_usd = npv_cop / spot

        return {
            "npv_cop": npv_cop,
            "npv_usd": npv_usd,
            "usd_leg_pv": usd_leg_value,
            "cop_leg_pv": cop_leg_value,
            "usd_notional_exchange_pv": usd_notional_pv,
            "cop_notional_exchange_pv": cop_notional_pv,
            "usd_total": usd_total,
            "cop_total": cop_total,
            "notional_usd": notional_usd,
            "notional_cop": notional_cop,
            "fx_initial": fx,
            "fx_spot": spot,
            "xccy_basis_bps": xccy_basis_bps,
            "start_date": ql_to_datetime(start_date),
            "maturity_date": ql_to_datetime(maturity_date),
        }

    def _value_ois_leg(
        self, schedule, notional, discount_handle, spread, day_counter
    ) -> float:
        """
        Value a floating OIS leg by computing forward rates and discounting.

        For each period:
          1. Compute forward rate from the curve
          2. Add the spread
          3. Compute accrued amount
          4. Discount to today
        """
        pv = 0.0
        dates = list(schedule)
        for i in range(1, len(dates)):
            start = dates[i - 1]
            end = dates[i]

            fwd_rate = discount_handle.forwardRate(
                start, end, day_counter, ql.Simple
            ).rate()

            tau = day_counter.yearFraction(start, end)
            cashflow = notional * (fwd_rate + spread) * tau
            df = discount_handle.discount(end)
            pv += cashflow * df

        return pv

    def par_xccy_basis(
        self,
        notional_usd: float,
        start_date,
        maturity_date,
        fx_initial: float = None,
        payment_frequency: ql.Period = ql.Period(3, ql.Months),
    ) -> float:
        """
        Find the par cross-currency basis spread (in bps) that makes NPV = 0.

        Returns:
            Par xccy basis spread in bps
        """

        def objective(basis_bps):
            result = self.price(
                notional_usd=notional_usd,
                start_date=start_date,
                maturity_date=maturity_date,
                xccy_basis_bps=basis_bps,
                fx_initial=fx_initial,
                payment_frequency=payment_frequency,
            )
            return result["npv_cop"]

        par_basis = brentq(objective, -5000, 5000, xtol=0.01)
        return par_basis

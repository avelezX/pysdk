"""
USD/COP Cross-Currency Swap pricer.

Structure:
  - USD leg: Floating SOFR overnight (compounded) + optional spread
  - COP leg: Floating IBR overnight (compounded) + xccy basis spread
  - Notional exchange at start, intermediate amortization returns, and final

Pricing uses dual-curve discounting:
  - COP cashflows discounted with IBR curve
  - USD cashflows discounted with SOFR curve
  - All values converted to common currency (COP) at FX spot

Supports amortizing notionals via amortization_schedule parameter.

Bancolombia CCS parameterization (typical):
  The confirmation shows -22bps on the SOFR/USD leg and IBR flat.
  Use: usd_spread_bps=-22, xccy_basis_bps=0
  NOT: xccy_basis_bps=-22 (which would put the spread on the COP leg).

Note: QuantLib Python bindings don't expose a native CrossCurrencyBasisSwap.
This implementation manually computes each leg's PV using forward rates
and discount factors — standard practice in production systems.
"""
import QuantLib as ql
import pandas as pd
from datetime import datetime
from scipy.optimize import brentq
from utilities.date_functions import datetime_to_ql, ql_to_datetime


# Standard amortization types
AMORTIZATION_TYPES = {
    "bullet": "No amortization — full notional exchanged at maturity",
    "linear": "Equal notional reductions each period",
    "custom": "User-provided schedule of notional factors per period",
}


def build_amortization_schedule(
    schedule,
    notional: float,
    amortization_type: str = "bullet",
    amortization_schedule: list = None,
) -> list:
    """
    Build a list of notionals per period given the amortization type.

    Args:
        schedule: QuantLib Schedule object
        notional: Original notional amount
        amortization_type: 'bullet', 'linear', or 'custom'
        amortization_schedule: For 'custom', a list of notional factors
            (e.g., [1.0, 1.0, 0.8, 0.6, 0.4, 0.2]) — one per period.
            Factor 1.0 = full notional, 0.5 = half, etc.

    Returns:
        List of notional amounts, one per coupon period.
    """
    n_periods = len(list(schedule)) - 1

    if amortization_type == "bullet" or amortization_type is None:
        return [notional] * n_periods

    elif amortization_type == "linear":
        # Linear amortization: notional decreases evenly
        # Period 1 = full, period n = 1/n of original
        factors = [(n_periods - i) / n_periods for i in range(n_periods)]
        return [notional * f for f in factors]

    elif amortization_type == "custom":
        if amortization_schedule is None:
            raise ValueError(
                "amortization_schedule is required for custom amortization"
            )
        if len(amortization_schedule) != n_periods:
            raise ValueError(
                f"amortization_schedule has {len(amortization_schedule)} entries "
                f"but schedule has {n_periods} periods"
            )
        return [notional * f for f in amortization_schedule]

    else:
        raise ValueError(
            f"Unknown amortization_type '{amortization_type}'. "
            f"Valid types: {list(AMORTIZATION_TYPES.keys())}"
        )


def validate_amortization_schedule(
    schedule_factors: list,
    tolerance: float = 1e-6,
) -> dict:
    """
    Validate an amortization schedule for consistency.

    Checks:
      - All factors are between 0 and 1
      - Factors are non-increasing (notional never goes up)
      - Last factor is > 0 (some residual notional remains)
      - First factor is 1.0 (starts at full notional)

    Args:
        schedule_factors: List of notional factors
        tolerance: Numerical tolerance for comparisons

    Returns:
        dict with 'valid' (bool), 'warnings' (list), 'errors' (list)
    """
    errors = []
    warnings = []

    if not schedule_factors:
        errors.append("Schedule is empty")
        return {"valid": False, "errors": errors, "warnings": warnings}

    # Check range
    for i, f in enumerate(schedule_factors):
        if f < -tolerance:
            errors.append(f"Period {i+1}: factor {f} is negative")
        if f > 1.0 + tolerance:
            errors.append(f"Period {i+1}: factor {f} exceeds 1.0")

    # Check first factor
    if abs(schedule_factors[0] - 1.0) > tolerance:
        warnings.append(
            f"First factor is {schedule_factors[0]}, expected 1.0 (full notional)"
        )

    # Check monotonicity
    for i in range(1, len(schedule_factors)):
        if schedule_factors[i] > schedule_factors[i - 1] + tolerance:
            warnings.append(
                f"Period {i+1}: factor {schedule_factors[i]:.4f} increases "
                f"from {schedule_factors[i-1]:.4f} (non-standard)"
            )

    # Check last factor
    if schedule_factors[-1] < tolerance:
        warnings.append("Last factor is 0 — notional fully amortized before maturity")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "n_periods": len(schedule_factors),
        "total_amortization_pct": (1.0 - schedule_factors[-1]) * 100
        if schedule_factors
        else 0,
    }


class XccySwapPricer:
    """
    Prices COP/USD Cross-Currency basis swaps.
    Requires CurveManager with IBR and SOFR curves, plus FX spot.

    Supports bullet and amortizing notional structures.
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
        amortization_type: str = "bullet",
        amortization_schedule: list = None,
    ) -> dict:
        """
        Price a cross-currency swap with optional amortization.

        Structure: Pay USD SOFR + usd_spread / Receive COP IBR + xccy_basis
                   (or reverse if pay_usd=False)

        For Bancolombia CCS confirmations the spread is typically on the
        SOFR leg (e.g., SOFR - 22bps).  Use usd_spread_bps=-22 and
        xccy_basis_bps=0.

        Args:
            notional_usd: USD notional amount
            start_date: Swap start date (datetime or ql.Date)
            maturity_date: Swap maturity date
            xccy_basis_bps: Cross-currency basis spread in bps (added to COP leg)
            pay_usd: If True, we pay USD and receive COP
            fx_initial: FX rate at inception for notional exchange
            cop_spread_bps: Additional spread on COP leg (bps)
            usd_spread_bps: Spread on USD/SOFR leg (bps), e.g. -22 for SOFR-22bps
            payment_frequency: Payment frequency for both legs
            amortization_type: 'bullet' (default), 'linear', or 'custom'
            amortization_schedule: For 'custom', list of notional factors per period

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

        # Always build the schedule from the original start_date so that
        # payment dates and amortization factors are consistent between
        # inception and mid-life pricing.  For mid-life, we filter out
        # past periods after building the full schedule.
        bdc = ql.Following
        schedule = ql.Schedule(
            start_date, maturity_date,
            payment_frequency,
            joint_cal,
            bdc, bdc,
            ql.DateGeneration.Forward, False,
        )

        # Build amortization notional arrays from the FULL schedule
        # (preserves correct amortization factors regardless of mid-life)
        usd_notionals = build_amortization_schedule(
            schedule, notional_usd, amortization_type, amortization_schedule
        )
        cop_notionals = [n * fx for n in usd_notionals]

        # For mid-life pricing, determine the first future period.
        # We need the curve reference dates to avoid "negative time" errors
        # when asking for discount/forward rates at past dates.
        full_dates = list(schedule)
        if is_midlife:
            sofr_ref = self.cm.sofr_handle.currentLink().referenceDate()
            ibr_ref = self.cm.ibr_handle.currentLink().referenceDate()
            curve_floor = max(eval_date, sofr_ref, ibr_ref)
            # Find the first period whose END date is still in the future.
            # Replace that period's start with curve_floor so forward rate
            # queries don't hit negative time.
            first_future = 0
            for i in range(1, len(full_dates)):
                if full_dates[i] > curve_floor:
                    first_future = i - 1
                    break
            future_dates = list(full_dates[first_future:])
            future_usd = list(usd_notionals[first_future:])
            future_cop = list(cop_notionals[first_future:])
            # Clip the start of the first remaining period to curve_floor
            if future_dates[0] < curve_floor:
                future_dates[0] = curve_floor
        else:
            future_dates = full_dates
            future_usd = usd_notionals
            future_cop = cop_notionals

        # USD Leg (SOFR floating)
        usd_leg_value = self._value_ois_leg_from_dates(
            future_dates, future_usd,
            self.cm.sofr_handle,
            usd_spread_bps / 10000.0,
            ql.Actual360(),
        )

        # COP Leg (IBR floating + xccy basis)
        total_cop_spread = (xccy_basis_bps + cop_spread_bps) / 10000.0
        cop_leg_value = self._value_ois_leg_from_dates(
            future_dates, future_cop,
            self.cm.ibr_handle,
            total_cop_spread,
            ql.Actual360(),
        )

        # Notional exchange PV
        # _notional_exchange_pv_amort returns from the payer's perspective:
        #   negative = pay out (initial), positive = receive back (amort/final).
        # For the NPV formula: npv = sign * (-usd_total * spot + cop_total)
        #   Both legs must be negated so that:
        #   - usd_notional_pv > 0 means net USD outflow (cost),
        #     which subtracts via -usd_total * spot.
        #   - cop_notional_pv > 0 means net COP inflow (benefit).
        if is_midlife:
            # Initial exchange already settled; only future returns remain.
            n_future = len(future_dates) - 1
            usd_notional_pv = 0.0
            cop_notional_pv = 0.0
            for i in range(1, n_future):
                usd_amort = future_usd[i - 1] - future_usd[i]
                cop_amort = future_cop[i - 1] - future_cop[i]
                if abs(usd_amort) > 1e-2:
                    usd_notional_pv -= usd_amort * self.cm.sofr_handle.discount(future_dates[i])
                if abs(cop_amort) > 1e-2:
                    cop_notional_pv -= cop_amort * self.cm.ibr_handle.discount(future_dates[i])
            # Final notional exchange at maturity
            usd_notional_pv -= future_usd[-1] * self.cm.sofr_handle.discount(future_dates[-1])
            cop_notional_pv -= future_cop[-1] * self.cm.ibr_handle.discount(future_dates[-1])
        else:
            usd_notional_pv = self._notional_exchange_pv_amort(
                schedule, usd_notionals, self.cm.sofr_handle
            )
            cop_notional_pv = self._notional_exchange_pv_amort(
                schedule, cop_notionals, self.cm.ibr_handle
            )
            usd_notional_pv = -usd_notional_pv
            cop_notional_pv = -cop_notional_pv

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
            "amortization_type": amortization_type,
            "start_date": ql_to_datetime(start_date),
            "maturity_date": ql_to_datetime(maturity_date),
        }

    def _value_ois_leg(
        self, schedule, notional, discount_handle, spread, day_counter
    ) -> float:
        """
        Value a floating OIS leg (bullet notional) by computing forward rates
        and discounting. Kept for backward compatibility.
        """
        return self._value_ois_leg_amort(
            schedule, None, discount_handle, spread, day_counter,
            fixed_notional=notional,
        )

    def _value_ois_leg_from_dates(
        self, dates, notionals, discount_handle, spread, day_counter,
    ) -> float:
        """
        Value a floating OIS leg from a list of period dates and notionals.

        For each period [dates[i-1], dates[i]]:
          1. Compute forward rate from the curve
          2. Add the spread
          3. Compute accrued amount using period notional
          4. Discount to today

        Args:
            dates: List of ql.Date (period boundaries)
            notionals: List of notional amounts per period (len = len(dates)-1)
            discount_handle: Curve handle for discounting/projection
            spread: Spread over the floating rate (decimal)
            day_counter: Day count convention
        """
        pv = 0.0
        for i in range(1, len(dates)):
            start = dates[i - 1]
            end = dates[i]
            notional = notionals[i - 1]

            fwd_rate = discount_handle.forwardRate(
                start, end, day_counter, ql.Simple
            ).rate()

            tau = day_counter.yearFraction(start, end)
            cashflow = notional * (fwd_rate + spread) * tau
            df = discount_handle.discount(end)
            pv += cashflow * df

        return pv

    def _value_ois_leg_amort(
        self, schedule, notionals, discount_handle, spread, day_counter,
        fixed_notional: float = None,
    ) -> float:
        """
        Value a floating OIS leg with per-period notionals.
        Kept for backward compatibility — delegates to _value_ois_leg_from_dates.
        """
        dates = list(schedule)
        if notionals is None:
            n = len(dates) - 1
            notionals = [fixed_notional] * n
        return self._value_ois_leg_from_dates(
            dates, notionals, discount_handle, spread, day_counter,
        )

    def _notional_exchange_pv_amort(
        self, schedule, notionals, discount_handle
    ) -> float:
        """
        Compute PV of notional exchanges for an amortizing swap.

        For a bullet swap: pay notional at start, receive at maturity.
        For an amortizing swap: initial exchange + intermediate amortization
        returns at each step-down date, + final exchange of remaining notional.

        Convention: negative = pay out, positive = receive back.

        Returns PV from the payer's perspective (pays notional initially).
        """
        dates = list(schedule)
        n_periods = len(dates) - 1

        pv = 0.0

        # Initial notional exchange: pay full notional at start
        pv -= notionals[0] * discount_handle.discount(dates[0])

        # Intermediate amortization returns and final exchange
        for i in range(1, n_periods):
            amort_return = notionals[i - 1] - notionals[i]
            if abs(amort_return) > 1e-2:
                # Receive back the amortized portion at period end
                pv += amort_return * discount_handle.discount(dates[i])

        # Final notional exchange: receive remaining notional at maturity
        pv += notionals[-1] * discount_handle.discount(dates[-1])

        return pv

    def pnl_inception(
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
        amortization_type: str = "bullet",
        amortization_schedule: list = None,
    ) -> dict:
        """
        P&L from inception decomposed into FX and rate components.

        At trade inception the xccy swap was at-par (NPV~0 at the contracted
        basis spread). The current NPV is attributed to:

          FX component:  change in NPV if only FX spot moved
          Rate component: change in NPV if only curves moved
          Cross-gamma:   residual interaction

        This uses the current price() method and re-prices under
        counterfactual scenarios by adjusting fx_initial vs fx_spot.

        Returns:
            dict with npv_total, pnl_fx, pnl_rates, pnl_cross
        """
        # Current full NPV
        current = self.price(
            notional_usd=notional_usd,
            start_date=start_date,
            maturity_date=maturity_date,
            xccy_basis_bps=xccy_basis_bps,
            pay_usd=pay_usd,
            fx_initial=fx_initial,
            cop_spread_bps=cop_spread_bps,
            usd_spread_bps=usd_spread_bps,
            payment_frequency=payment_frequency,
            amortization_type=amortization_type,
            amortization_schedule=amortization_schedule,
        )
        npv_total = current["npv_cop"]

        # The inception FX is fx_initial (or cm.fx_spot if not specified)
        fx_inc = fx_initial or self.cm.fx_spot
        fx_now = self.cm.fx_spot

        # FX-only P&L: the difference between NPV at current FX and NPV at
        # inception FX, with curves as-is. Since price() always uses
        # cm.fx_spot for conversion, we compute the sensitivity directly.
        # NPV_cop ~ sign * (-USD_total * fx_spot + COP_total)
        # FX component = sign * (-USD_total) * (fx_now - fx_inc)
        sign = 1.0 if pay_usd else -1.0
        pnl_fx = sign * (-current["usd_total"]) * (fx_now - fx_inc)

        # Rate-only P&L: total minus FX component minus cross
        # Since cross-gamma is second order, approximate rate P&L as:
        pnl_rates = npv_total - pnl_fx

        return {
            "npv_cop": npv_total,
            "npv_usd": current["npv_usd"],
            "pnl_fx_cop": pnl_fx,
            "pnl_rates_cop": pnl_rates,
            "fx_initial": fx_inc,
            "fx_spot": fx_now,
            "usd_total": current["usd_total"],
            "cop_total": current["cop_total"],
            "xccy_basis_bps": xccy_basis_bps,
            "amortization_type": amortization_type,
            "start_date": current["start_date"],
            "maturity_date": current["maturity_date"],
        }

    def par_xccy_basis(
        self,
        notional_usd: float,
        start_date,
        maturity_date,
        fx_initial: float = None,
        payment_frequency: ql.Period = ql.Period(3, ql.Months),
        amortization_type: str = "bullet",
        amortization_schedule: list = None,
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
                amortization_type=amortization_type,
                amortization_schedule=amortization_schedule,
            )
            return result["npv_cop"]

        par_basis = brentq(objective, -5000, 5000, xtol=0.01)
        return par_basis

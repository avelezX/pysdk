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
        Price a USD/COP Cross-Currency Swap with optional amortization.

        Structure (pay_usd=True, standard Bancolombia):
            Golosinas/client  PAYS  USD leg: SOFR + usd_spread_bps
            Bancolombia       PAYS  COP leg: IBR + xccy_basis_bps + cop_spread_bps

        Spread convention (Bancolombia confirmations):
            Spread on the USD leg  → usd_spread_bps=-22, xccy_basis_bps=0
            Spread on the COP leg  → usd_spread_bps=0,   xccy_basis_bps=-22
            Both legs flat        → usd_spread_bps=0,   xccy_basis_bps=0

        Mid-life pricing:
            When start_date < today, the initial notional exchange is treated as
            already settled. Only future cashflows and notional returns are priced.

        Args:
            notional_usd (float): USD notional at inception. Must be > 0.
            start_date (datetime | ql.Date): Trade start date (T+0 of the swap).
            maturity_date (datetime | ql.Date): Final maturity date.
            xccy_basis_bps (float): Spread added to the COP/IBR leg, in bps.
                Positive = client receives more COP interest.
            pay_usd (bool): True = client pays USD, receives COP (standard).
                False = client receives USD, pays COP.
            fx_initial (float | None): USD/COP FX rate used for the notional
                exchange at inception. If None, uses current cm.fx_spot.
            cop_spread_bps (float): Additional spread on COP leg, in bps.
                Usually 0; use xccy_basis_bps for the basis.
            usd_spread_bps (float): Spread on the SOFR/USD leg, in bps.
                Use -22 for SOFR-22bps.
            payment_frequency (ql.Period): Coupon frequency for both legs.
                Typical values: ql.Period(1, ql.Months)  — monthly
                                ql.Period(3, ql.Months)  — quarterly (default)
                                ql.Period(6, ql.Months)  — semi-annual
                                ql.Period(12, ql.Months) — annual
            amortization_type (str): Notional amortization profile.
                'bullet'  — no intermediate amortization (default)
                'linear'  — equal notional step-downs each period
                'custom'  — user-provided factors via amortization_schedule
            amortization_schedule (list | None): Required when amortization_type
                is 'custom'. List of notional factors (floats 0–1), one per period,
                e.g. [1.0, 0.875, 0.75, 0.625, 0.5, 0.375, 0.25, 0.125]
                for 8 equal quarterly amortizations.

        Returns:
            dict with the following keys:
                npv_cop (float): Net present value in COP from the client's perspective.
                    Positive = swap has positive value for the client.
                npv_usd (float): NPV converted to USD at current fx_spot.
                usd_leg_pv (float): PV of future USD interest cashflows (USD).
                cop_leg_pv (float): PV of future COP interest cashflows (COP).
                usd_notional_exchange_pv (float): PV of net USD notional flows (USD).
                    At inception: large negative (client pays USD upfront).
                    Mid-life: PV of remaining amortization + final return.
                cop_notional_exchange_pv (float): PV of net COP notional flows (COP).
                usd_total (float): usd_leg_pv + usd_notional_exchange_pv (USD).
                cop_total (float): cop_leg_pv + cop_notional_exchange_pv (COP).
                notional_usd (float): Original USD notional.
                notional_cop (float): Equivalent COP notional = notional_usd * fx_initial.
                fx_initial (float): FX rate used for the notional exchange.
                fx_spot (float): Current USD/COP spot rate used for NPV conversion.
                xccy_basis_bps (float): Echo of the input parameter.
                amortization_type (str): Echo of the input parameter.
                start_date (datetime): Trade start date.
                maturity_date (datetime): Trade maturity date.
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
            first_future = None
            for i in range(1, len(full_dates)):
                if full_dates[i] > curve_floor:
                    first_future = i - 1
                    break
            if first_future is None:
                # All periods have already settled — swap is fully expired.
                return {
                    "npv_cop": 0.0, "npv_usd": 0.0,
                    "usd_leg_pv": 0.0, "cop_leg_pv": 0.0,
                    "usd_notional_exchange_pv": 0.0, "cop_notional_exchange_pv": 0.0,
                    "usd_total": 0.0, "cop_total": 0.0,
                    "notional_usd": notional_usd, "notional_cop": notional_cop,
                    "fx_initial": fx, "fx_spot": self.cm.fx_spot,
                    "xccy_basis_bps": xccy_basis_bps,
                    "amortization_type": amortization_type,
                    "start_date": ql_to_datetime(start_date),
                    "maturity_date": ql_to_datetime(maturity_date),
                    # Tier 2 — expired swap
                    "days_open": (ql_to_datetime(eval_date) - ql_to_datetime(start_date)).days,
                    "periods_remaining": 0,
                    "current_period": None,
                    "carry_daily_cop": 0.0,
                    "carry_accrued_cop": 0.0,
                    "fx_delta_cop": 0.0,
                }
            future_dates = list(full_dates[first_future:])
            future_usd = list(usd_notionals[first_future:])
            future_cop = list(cop_notionals[first_future:])
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

        # Notional exchange PV — gross convention (same as notebook)
        # usd_notional_pv = PV of all USD paid (outflows, positive)
        # cop_notional_pv = PV of all COP received (inflows, positive)
        # Formula: npv = sign * (-usd_total * spot + cop_total) works correctly when
        # usd_total = coupons_paid + notional_paid and cop_total = coupons_received + notional_received.
        if is_midlife:
            # T0 exchange already settled; only future amortization flows remain.
            n_future = len(future_dates) - 1
            usd_notional_pv = 0.0
            cop_notional_pv = 0.0
            for i in range(1, n_future):
                usd_amort = future_usd[i - 1] - future_usd[i]
                cop_amort = future_cop[i - 1] - future_cop[i]
                if abs(usd_amort) > 1e-2:
                    usd_notional_pv += usd_amort * self.cm.sofr_handle.discount(future_dates[i])
                if abs(cop_amort) > 1e-2:
                    cop_notional_pv += cop_amort * self.cm.ibr_handle.discount(future_dates[i])
            # Final notional exchange at maturity
            usd_notional_pv += future_usd[-1] * self.cm.sofr_handle.discount(future_dates[-1])
            cop_notional_pv += future_cop[-1] * self.cm.ibr_handle.discount(future_dates[-1])
        else:
            # Inception: T0 exchange + all future amortizations (gross outflows/inflows).
            # SOFR T+2 fix: clip T0 date to curve referenceDate (discount(ref) = 1.0).
            sofr_ref = self.cm.sofr_handle.currentLink().referenceDate()
            ibr_ref  = self.cm.ibr_handle.currentLink().referenceDate()
            t0 = full_dates[0]
            sofr_t0 = sofr_ref if t0 < sofr_ref else t0
            ibr_t0  = ibr_ref  if t0 < ibr_ref  else t0
            usd_notional_pv = usd_notionals[0] * self.cm.sofr_handle.discount(sofr_t0)
            cop_notional_pv = cop_notionals[0] * self.cm.ibr_handle.discount(ibr_t0)
            n_periods = len(full_dates) - 1
            for i in range(1, n_periods):
                usd_amort = usd_notionals[i - 1] - usd_notionals[i]
                cop_amort = cop_notionals[i - 1] - cop_notionals[i]
                if abs(usd_amort) > 1e-2:
                    usd_notional_pv += usd_amort * self.cm.sofr_handle.discount(full_dates[i])
                if abs(cop_amort) > 1e-2:
                    cop_notional_pv += cop_amort * self.cm.ibr_handle.discount(full_dates[i])
            # Final notional exchange at maturity
            usd_notional_pv += usd_notionals[-1] * self.cm.sofr_handle.discount(full_dates[-1])
            cop_notional_pv += cop_notionals[-1] * self.cm.ibr_handle.discount(full_dates[-1])

        usd_total = usd_leg_value + usd_notional_pv
        cop_total = cop_leg_value + cop_notional_pv

        spot = self.cm.fx_spot
        sign = 1.0 if pay_usd else -1.0
        npv_cop = sign * (-usd_total * spot + cop_total)
        npv_usd = npv_cop / spot

        # ── Tier 2: carry and period metadata ────────────────────────────────
        eval_dt   = ql_to_datetime(eval_date)
        start_dt  = ql_to_datetime(start_date)
        days_open = (eval_dt - start_dt).days

        # Current accrual period — future_dates[0]/[1] work for both
        # inception (= full_dates[0:2]) and mid-life (= full_dates[first_future:first_future+2])
        cur_p_start  = future_dates[0]
        cur_p_end    = future_dates[1]
        cur_n_usd    = future_usd[0]
        cur_n_cop    = future_cop[0]
        days_elapsed = max(0, (eval_dt - ql_to_datetime(cur_p_start)).days)

        # Forward rates for the current period (clip start to referenceDate)
        sofr_ref_fwd = self.cm.sofr_handle.currentLink().referenceDate()
        ibr_ref_fwd  = self.cm.ibr_handle.currentLink().referenceDate()
        dc           = ql.Actual360()
        sofr_p_start = cur_p_start if cur_p_start >= sofr_ref_fwd else sofr_ref_fwd
        ibr_p_start  = cur_p_start if cur_p_start >= ibr_ref_fwd  else ibr_ref_fwd

        ibr_fwd_rate  = self.cm.ibr_handle.forwardRate(
            ibr_p_start, cur_p_end, dc, ql.Simple).rate()
        sofr_fwd_rate = self.cm.sofr_handle.forwardRate(
            sofr_p_start, cur_p_end, dc, ql.Simple).rate()

        usd_spread_dec    = usd_spread_bps / 10_000.0
        # total_cop_spread already computed above (xccy_basis + cop_spread)
        carry_daily_cop   = sign * (
            cur_n_cop * (ibr_fwd_rate + total_cop_spread)
            - cur_n_usd * (sofr_fwd_rate + usd_spread_dec) * spot
        ) / 360.0
        carry_accrued_cop = carry_daily_cop * days_elapsed

        # FX delta: d(npv_cop)/d(spot) = sign * (-usd_total)
        fx_delta_cop      = sign * (-usd_total)
        periods_remaining = len(future_dates) - 1

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
            # Tier 2
            "days_open": days_open,
            "periods_remaining": periods_remaining,
            "current_period": {
                "start":           ql_to_datetime(cur_p_start).strftime("%Y-%m-%d"),
                "end":             ql_to_datetime(cur_p_end).strftime("%Y-%m-%d"),
                "days_elapsed":    days_elapsed,
                "notional_usd":    cur_n_usd,
                "notional_cop":    cur_n_cop,
                "ibr_fwd_pct":     round(ibr_fwd_rate * 100, 6),
                "sofr_fwd_pct":    round(sofr_fwd_rate * 100, 6),
                "differential_bps": round((ibr_fwd_rate - sofr_fwd_rate) * 10_000, 2),
            },
            "carry_daily_cop":   carry_daily_cop,
            "carry_accrued_cop": carry_accrued_cop,
            "fx_delta_cop":      fx_delta_cop,
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
          1. Compute forward rate from the curve (start clipped to referenceDate
             to avoid negative-time errors for curves with settlement lag, e.g. SOFR T+2)
          2. Add the spread
          3. Compute accrued amount using period notional and ORIGINAL tau (not clipped)
          4. Discount to today

        Args:
            dates: List of ql.Date (period boundaries)
            notionals: List of notional amounts per period (len = len(dates)-1)
            discount_handle: Curve handle for discounting/projection
            spread: Spread over the floating rate (decimal)
            day_counter: Day count convention
        """
        ref_date = discount_handle.referenceDate()
        pv = 0.0
        for i in range(1, len(dates)):
            start = dates[i - 1]
            end = dates[i]
            notional = notionals[i - 1]

            # Clip start to referenceDate only for forward rate query.
            # tau always uses the original period dates (preserves coupon accrual).
            fwd_start = start if start >= ref_date else ref_date
            fwd_rate = discount_handle.forwardRate(
                fwd_start, end, day_counter, ql.Simple
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

        Note: The initial exchange date is clipped to the curve's referenceDate
        to avoid negative-time errors for curves with settlement lag (e.g. SOFR T+2).
        discount(referenceDate) = 1.0 exactly, so the economic error is zero.
        """
        dates = list(schedule)
        n_periods = len(dates) - 1

        ref_date = discount_handle.referenceDate()

        # Initial notional exchange: pay full notional at start.
        # Clip to referenceDate: discount(ref_date) = 1.0, so no economic error.
        initial_date = dates[0] if dates[0] >= ref_date else ref_date
        pv = -notionals[0] * discount_handle.discount(initial_date)

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

    def cashflows(
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
    ) -> list:
        """
        Full cashflow schedule for a USD/COP Cross-Currency Swap.

        Returns one dict per period (period 0 = inception notional exchange,
        periods 1..N = coupon + amortization periods).

        Convention (pay_usd=True):
            usd_net  negative = client pays USD outflow
            cop_net  positive = client receives COP inflow
            status   'settled' (past), 'current' (active accrual), 'future'

        For settled periods, forward rates and coupon amounts are None
        (actual realized rates are not stored in the curve).
        """
        if isinstance(start_date, datetime):
            start_date = datetime_to_ql(start_date)
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        fx = fx_initial or self.cm.fx_spot
        notional_cop = notional_usd * fx

        cop_cal = self.cm.ibr_index.fixingCalendar()
        usd_cal = self.cm.sofr_index.fixingCalendar()
        joint_cal = ql.JointCalendar(cop_cal, usd_cal)
        bdc = ql.Following
        schedule = ql.Schedule(
            start_date, maturity_date,
            payment_frequency,
            joint_cal, bdc, bdc,
            ql.DateGeneration.Forward, False,
        )

        usd_notionals = build_amortization_schedule(
            schedule, notional_usd, amortization_type, amortization_schedule
        )
        cop_notionals = [n * fx for n in usd_notionals]
        dates = list(schedule)
        n_periods = len(dates) - 1

        eval_date   = ql.Settings.instance().evaluationDate
        sofr_ref    = self.cm.sofr_handle.currentLink().referenceDate()
        ibr_ref     = self.cm.ibr_handle.currentLink().referenceDate()
        dc          = ql.Actual360()
        usd_spd_dec = usd_spread_bps / 10_000.0
        cop_spd_dec = (xccy_basis_bps + cop_spread_bps) / 10_000.0
        sign        = 1.0 if pay_usd else -1.0

        rows = []

        # ── Period 0: inception notional exchange ────────────────────────────
        t0     = dates[0]
        t0_str = ql_to_datetime(t0).strftime("%Y-%m-%d")
        rows.append({
            "period_num":   0,
            "date_start":   t0_str,
            "date_end":     t0_str,
            "notional_usd": notional_usd,
            "notional_cop": notional_cop,
            "usd_coupon":   None,
            "cop_coupon":   None,
            "usd_principal": round(-sign * notional_usd, 2),  # client pays USD
            "cop_principal": round(+sign * notional_cop, 0),  # client receives COP
            "usd_net":       round(-sign * notional_usd, 2),
            "cop_net":       round(+sign * notional_cop, 0),
            "ibr_fwd_pct":  None,
            "sofr_fwd_pct": None,
            "status":       "settled" if t0 <= eval_date else "future",
        })

        # ── Periods 1..N: coupons + amortization ─────────────────────────────
        for i in range(1, n_periods + 1):
            p_start = dates[i - 1]
            p_end   = dates[i]
            N_usd   = usd_notionals[i - 1]
            N_cop   = cop_notionals[i - 1]

            if p_end <= eval_date:
                status = "settled"
            elif p_start < eval_date:
                status = "current"
            else:
                status = "future"

            # Forward rates only for current/future periods (settled = not in curve)
            if status != "settled" and p_end > sofr_ref and p_end > ibr_ref:
                sofr_start = p_start if p_start >= sofr_ref else sofr_ref
                ibr_start  = p_start if p_start >= ibr_ref  else ibr_ref
                tau        = dc.yearFraction(p_start, p_end)
                sofr_fwd   = self.cm.sofr_handle.forwardRate(
                    sofr_start, p_end, dc, ql.Simple).rate()
                ibr_fwd    = self.cm.ibr_handle.forwardRate(
                    ibr_start, p_end, dc, ql.Simple).rate()
                usd_coupon = round(N_usd * (sofr_fwd + usd_spd_dec) * tau, 2)
                cop_coupon = round(N_cop * (ibr_fwd  + cop_spd_dec) * tau, 0)
                ibr_pct    = round(ibr_fwd * 100, 4)
                sofr_pct   = round(sofr_fwd * 100, 4)
            else:
                usd_coupon = sofr_fwd = sofr_pct = None
                cop_coupon = ibr_fwd  = ibr_pct  = None

            # Principal flows at period end (deterministic, always known)
            if i < n_periods:
                usd_amort = usd_notionals[i - 1] - usd_notionals[i]
                cop_amort = cop_notionals[i - 1] - cop_notionals[i]
            else:  # final: return remaining notional
                usd_amort = usd_notionals[-1]
                cop_amort = cop_notionals[-1]

            # Client perspective (pay_usd=True: pays USD coupons, receives COP coupons)
            # At amortizations: receives USD back (+), returns COP (-)
            usd_principal = round(sign * usd_amort, 2)   # + = receive back
            cop_principal = round(-sign * cop_amort, 0)  # - = return

            usd_net = round((-sign * (usd_coupon or 0.0)) + usd_principal, 2)
            cop_net = round((+sign * (cop_coupon or 0.0)) + cop_principal, 0)

            rows.append({
                "period_num":    i,
                "date_start":    ql_to_datetime(p_start).strftime("%Y-%m-%d"),
                "date_end":      ql_to_datetime(p_end).strftime("%Y-%m-%d"),
                "notional_usd":  N_usd,
                "notional_cop":  N_cop,
                "usd_coupon":    usd_coupon,
                "cop_coupon":    cop_coupon,
                "usd_principal": usd_principal,
                "cop_principal": cop_principal,
                "usd_net":       usd_net,
                "cop_net":       cop_net,
                "ibr_fwd_pct":   ibr_pct,
                "sofr_fwd_pct":  sofr_pct,
                "status":        status,
            })

        return rows

    def par_xccy_basis(
        self,
        notional_usd: float,
        start_date,
        maturity_date,
        fx_initial: float = None,
        usd_spread_bps: float = 0.0,
        cop_spread_bps: float = 0.0,
        pay_usd: bool = True,
        payment_frequency: ql.Period = ql.Period(3, ql.Months),
        amortization_type: str = "bullet",
        amortization_schedule: list = None,
    ) -> float:
        """
        Find the par cross-currency basis spread (in bps) that makes NPV = 0.

        The par basis is the xccy_basis_bps added to the COP leg such that
        NPV = 0, holding all other spreads fixed.

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
                usd_spread_bps=usd_spread_bps,
                cop_spread_bps=cop_spread_bps,
                pay_usd=pay_usd,
                payment_frequency=payment_frequency,
                amortization_type=amortization_type,
                amortization_schedule=amortization_schedule,
            )
            return result["npv_cop"]

        par_basis = brentq(objective, -5000, 5000, xtol=0.01)
        return par_basis

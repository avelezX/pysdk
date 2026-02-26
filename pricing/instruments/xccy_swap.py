"""
USD/COP Cross-Currency Swap (CCS) pricer.

Structure (Colombian convention):
  - USD leg: Floating SOFR (compounded quarterly) + xccy basis spread
  - COP leg: Floating IBR (nominal trimestral) flat (or + spread)
  - Non-Delivery settlement: net flows in COP at pactation FX rate

Supports:
  - Bullet, linear, and custom amortization schedules
  - Detailed cashflow generation per period
  - Par xccy basis solver (spread that makes NPV = 0)

Pricing uses dual-curve discounting:
  - USD cashflows discounted with SOFR curve
  - COP cashflows discounted with IBR curve
  - All values converted to common currency (COP) at FX spot

Note: QuantLib Python bindings don't expose a native CrossCurrencyBasisSwap.
This implementation manually computes each leg's PV using forward rates
and discount factors — standard practice in production systems.
"""
import QuantLib as ql
from datetime import datetime
from scipy.optimize import brentq
from utilities.date_functions import datetime_to_ql, ql_to_datetime


# Map frequency strings to QuantLib Periods
_FREQ_MAP = {
    "1M": ql.Period(1, ql.Months),
    "3M": ql.Period(3, ql.Months),
    "6M": ql.Period(6, ql.Months),
    "12M": ql.Period(12, ql.Months),
}


def _build_amortization_schedule(
    n_periods: int,
    amortization_type: str,
    amortization_schedule: list = None,
) -> list:
    """
    Build a list of remaining-notional fractions for each period.

    Returns:
        List of length n_periods where each element is the fraction of
        original notional outstanding DURING that period (for interest calc).
        Also returns amort_pcts: fraction amortized at end of each period.
    """
    if amortization_type == "bullet":
        remaining = [1.0] * n_periods
        amort_pcts = [0.0] * n_periods
        amort_pcts[-1] = 1.0  # Full principal at maturity
        return remaining, amort_pcts

    if amortization_type == "linear":
        amort_per_period = 1.0 / n_periods
        remaining = []
        amort_pcts = []
        for i in range(n_periods):
            remaining.append(1.0 - i * amort_per_period)
            amort_pcts.append(amort_per_period)
        return remaining, amort_pcts

    if amortization_type == "custom":
        if not amortization_schedule or len(amortization_schedule) != n_periods:
            raise ValueError(
                f"Custom schedule must have exactly {n_periods} entries "
                f"(remaining fractions), got {len(amortization_schedule) if amortization_schedule else 0}"
            )
        remaining = list(amortization_schedule)
        amort_pcts = []
        for i in range(n_periods):
            prev = remaining[i - 1] if i > 0 else 1.0
            amort_pcts.append(prev - remaining[i] if i < n_periods - 1 else remaining[i])
        return remaining, amort_pcts

    raise ValueError(f"Unknown amortization_type: '{amortization_type}'. Use 'bullet', 'linear', or 'custom'.")


class XccySwapPricer:
    """
    Prices COP/USD Cross-Currency basis swaps with amortization support.

    Colombian convention:
      - USD leg: SOFR + xccy basis (usd_spread_bps)
      - COP leg: IBR flat (or + cop_spread_bps)
      - Non-Delivery: flows netted in COP at pactation FX rate

    Requires CurveManager with IBR and SOFR curves, plus FX spot.
    """

    def __init__(self, curve_manager):
        self.cm = curve_manager

    def price(
        self,
        notional_usd: float,
        start_date,
        maturity_date,
        usd_spread_bps: float = 0.0,
        cop_spread_bps: float = 0.0,
        pay_usd: bool = True,
        fx_initial: float = None,
        payment_frequency: str = "3M",
        amortization_type: str = "bullet",
        amortization_schedule: list = None,
        _compute_par_basis: bool = True,
    ) -> dict:
        """
        Price a cross-currency swap.

        Colombian convention:
          Pay USD: SOFR + usd_spread_bps / Receive COP: IBR + cop_spread_bps
          (or reverse if pay_usd=False)

        Args:
            notional_usd: USD notional amount (initial)
            start_date: Swap start date (datetime or ql.Date)
            maturity_date: Swap maturity date
            usd_spread_bps: Spread on USD/SOFR leg in bps (this IS the xccy basis, e.g. -22)
            cop_spread_bps: Spread on COP/IBR leg in bps (usually 0)
            pay_usd: If True, we pay USD leg and receive COP leg
            fx_initial: FX rate at inception (default: current spot)
            payment_frequency: "1M", "3M", "6M", "12M"
            amortization_type: "bullet", "linear", or "custom"
            amortization_schedule: For "custom": list of remaining fractions per period

        Returns:
            dict with NPV, leg values, par basis, detailed cashflows
        """
        if isinstance(start_date, datetime):
            start_date = datetime_to_ql(start_date)
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        fx = fx_initial if fx_initial is not None else self.cm.fx_spot
        notional_cop = notional_usd * fx
        spot = self.cm.fx_spot

        freq = _FREQ_MAP.get(payment_frequency)
        if freq is None:
            raise ValueError(f"Unknown frequency '{payment_frequency}'. Use: {list(_FREQ_MAP.keys())}")

        usd_spread = usd_spread_bps / 10000.0
        cop_spread = cop_spread_bps / 10000.0
        day_counter = ql.Actual360()

        # Build payment schedule
        cop_cal = self.cm.ibr_index.fixingCalendar()
        usd_cal = self.cm.sofr_index.fixingCalendar()
        joint_cal = ql.JointCalendar(cop_cal, usd_cal)

        schedule = ql.Schedule(
            start_date, maturity_date,
            freq, joint_cal,
            ql.ModifiedFollowing, ql.ModifiedFollowing,
            ql.DateGeneration.Forward, False,
        )
        dates = list(schedule)
        n_periods = len(dates) - 1

        if n_periods < 1:
            raise ValueError("Schedule produces zero periods. Check start/maturity dates.")

        # Build amortization schedule
        remaining, amort_pcts = _build_amortization_schedule(
            n_periods, amortization_type, amortization_schedule
        )

        # Generate cashflows
        cashflows = []
        usd_interest_pv = 0.0
        cop_interest_pv = 0.0
        usd_principal_pv = 0.0
        cop_principal_pv = 0.0

        # Carry: capture the first future period's rates and net interest
        carry_cop = 0.0
        carry_rate_cop_pct = 0.0
        carry_rate_usd_pct = 0.0
        carry_differential_bps = 0.0
        carry_period_found = False

        # Use curve reference dates (accounts for settlement days) not valuation_date
        # Curves may have referenceDate = valuation_date + settlement_days
        sofr_ref = self.cm.sofr_handle.referenceDate()
        ibr_ref = self.cm.ibr_handle.referenceDate()
        curve_ref = max(sofr_ref, ibr_ref)

        for i in range(n_periods):
            period_start = dates[i]
            period_end = dates[i + 1]

            # Notional outstanding for this period
            not_usd_i = notional_usd * remaining[i]
            not_cop_i = notional_cop * remaining[i]

            # Period is past if payment date is on or before the curve reference date
            period_is_past = period_end <= curve_ref

            if period_is_past:
                usd_fwd = 0.0
                cop_fwd = 0.0
                usd_df = 0.0
                cop_df = 0.0
            else:
                # Clamp forward start to curve reference date (never before it)
                fwd_start = max(period_start, curve_ref)

                # Safety: ensure positive-length interval for forward rate
                if fwd_start >= period_end:
                    usd_fwd = 0.0
                    cop_fwd = 0.0
                else:
                    usd_fwd = self.cm.sofr_handle.forwardRate(
                        fwd_start, period_end, day_counter, ql.Simple
                    ).rate()
                    cop_fwd = self.cm.ibr_handle.forwardRate(
                        fwd_start, period_end, day_counter, ql.Simple
                    ).rate()

                usd_df = self.cm.sofr_handle.discount(period_end)
                cop_df = self.cm.ibr_handle.discount(period_end)

            tau = day_counter.yearFraction(period_start, period_end)

            # Interest cashflows
            usd_interest = not_usd_i * (usd_fwd + usd_spread) * tau
            cop_interest = not_cop_i * (cop_fwd + cop_spread) * tau

            # Carry: capture from the first future period (currently accruing)
            if not period_is_past and not carry_period_found:
                carry_period_found = True
                carry_cop = sign * (cop_interest - usd_interest * fx)
                carry_rate_cop_pct = round(cop_fwd * 100, 4)
                carry_rate_usd_pct = round((usd_fwd + usd_spread) * 100, 4)
                carry_differential_bps = round((cop_fwd - usd_fwd - usd_spread) * 10000, 1)

            # Principal amortization for this period
            usd_principal = notional_usd * amort_pcts[i]
            cop_principal = notional_cop * amort_pcts[i]

            # Present values (past periods don't contribute)
            if not period_is_past:
                usd_interest_pv += usd_interest * usd_df
                cop_interest_pv += cop_interest * cop_df
                usd_principal_pv += usd_principal * usd_df
                cop_principal_pv += cop_principal * cop_df

            # Non-Delivery net flow (in COP at pactation FX)
            net_cop = (cop_interest + cop_principal) - (usd_interest + usd_principal) * fx

            cashflows.append({
                "period": i + 1,
                "start": ql_to_datetime(period_start).strftime("%Y-%m-%d"),
                "end": ql_to_datetime(period_end).strftime("%Y-%m-%d"),
                "payment_date": ql_to_datetime(period_end).strftime("%Y-%m-%d"),
                "notional_usd": round(not_usd_i, 2),
                "notional_cop": round(not_cop_i, 2),
                "remaining_pct": round(remaining[i] * 100, 2),
                "usd_rate": round(usd_fwd * 100, 4),
                "cop_rate": round(cop_fwd * 100, 4),
                "usd_interest": round(usd_interest, 2),
                "cop_interest": round(cop_interest, 2),
                "usd_principal": round(usd_principal, 2),
                "cop_principal": round(cop_principal, 2),
                "usd_df": round(usd_df, 6),
                "cop_df": round(cop_df, 6),
                "net_cop": round(net_cop, 2),
            })

        # Total leg PVs
        usd_total_pv = usd_interest_pv + usd_principal_pv
        cop_total_pv = cop_interest_pv + cop_principal_pv

        # NPV: from perspective of pay_usd side
        # pay_usd=True: I pay USD leg, receive COP leg
        # NPV = (what I receive) - (what I pay), all in COP
        sign = 1.0 if pay_usd else -1.0
        npv_cop = sign * (cop_total_pv - usd_total_pv * spot)
        npv_usd = npv_cop / spot

        # P&L decomposition: FX effect vs Rate effect
        # Rate P&L: NPV as if FX stayed at pactation level (isolates rate differential)
        # FX P&L: additional gain/loss from FX movement
        pnl_rate_cop = sign * (cop_total_pv - usd_total_pv * fx)
        pnl_fx_cop = sign * usd_total_pv * (fx - spot)
        # npv_cop = pnl_rate_cop + pnl_fx_cop (by construction)
        pnl_rate_usd = pnl_rate_cop / spot
        pnl_fx_usd = pnl_fx_cop / spot

        # Compute par xccy basis (skip during solver to prevent infinite recursion)
        if _compute_par_basis:
            try:
                par_basis = self._par_xccy_basis_internal(
                    notional_usd=notional_usd,
                    start_date=start_date,
                    maturity_date=maturity_date,
                    cop_spread_bps=cop_spread_bps,
                    pay_usd=pay_usd,
                    fx_initial=fx_initial,
                    payment_frequency=payment_frequency,
                    amortization_type=amortization_type,
                    amortization_schedule=amortization_schedule,
                )
            except Exception:
                par_basis = None
        else:
            par_basis = None

        return {
            "npv_cop": round(npv_cop, 2),
            "npv_usd": round(npv_usd, 2),
            "pnl_rate_cop": round(pnl_rate_cop, 2),
            "pnl_rate_usd": round(pnl_rate_usd, 2),
            "pnl_fx_cop": round(pnl_fx_cop, 2),
            "pnl_fx_usd": round(pnl_fx_usd, 2),
            "usd_leg_pv": round(usd_interest_pv, 2),
            "cop_leg_pv": round(cop_interest_pv, 2),
            "usd_principal_pv": round(usd_principal_pv, 2),
            "cop_principal_pv": round(cop_principal_pv, 2),
            "par_basis_bps": round(par_basis, 2) if par_basis is not None else None,
            "carry_cop": round(carry_cop, 2),
            "carry_usd": round(carry_cop / spot, 2) if spot else 0,
            "carry_rate_cop_pct": carry_rate_cop_pct,
            "carry_rate_usd_pct": carry_rate_usd_pct,
            "carry_differential_bps": carry_differential_bps,
            "notional_usd": notional_usd,
            "notional_cop": notional_cop,
            "fx_initial": fx,
            "fx_spot": spot,
            "usd_spread_bps": usd_spread_bps,
            "cop_spread_bps": cop_spread_bps,
            "amortization_type": amortization_type,
            "payment_frequency": payment_frequency,
            "start_date": ql_to_datetime(start_date).strftime("%Y-%m-%d"),
            "maturity_date": ql_to_datetime(maturity_date).strftime("%Y-%m-%d"),
            "n_periods": n_periods,
            "cashflows": cashflows,
        }

    def _precompute_periods(
        self,
        notional_usd: float,
        start_date,
        maturity_date,
        cop_spread_bps: float,
        pay_usd: bool,
        fx_initial: float,
        payment_frequency: str,
        amortization_type: str,
        amortization_schedule: list,
    ) -> dict:
        """Pre-compute schedule data that doesn't change when USD spread varies."""
        if isinstance(start_date, datetime):
            start_date = datetime_to_ql(start_date)
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        fx = fx_initial if fx_initial is not None else self.cm.fx_spot
        notional_cop = notional_usd * fx
        spot = self.cm.fx_spot
        cop_spread = cop_spread_bps / 10000.0
        day_counter = ql.Actual360()

        freq = _FREQ_MAP.get(payment_frequency)
        cop_cal = self.cm.ibr_index.fixingCalendar()
        usd_cal = self.cm.sofr_index.fixingCalendar()
        joint_cal = ql.JointCalendar(cop_cal, usd_cal)

        schedule = ql.Schedule(
            start_date, maturity_date, freq, joint_cal,
            ql.ModifiedFollowing, ql.ModifiedFollowing,
            ql.DateGeneration.Forward, False,
        )
        dates = list(schedule)
        n_periods = len(dates) - 1
        remaining, amort_pcts = _build_amortization_schedule(
            n_periods, amortization_type, amortization_schedule
        )

        sofr_ref = self.cm.sofr_handle.referenceDate()
        ibr_ref = self.cm.ibr_handle.referenceDate()
        curve_ref = max(sofr_ref, ibr_ref)
        sign = 1.0 if pay_usd else -1.0

        # Pre-compute per-period invariants
        periods = []
        cop_interest_pv = 0.0
        cop_principal_pv = 0.0
        usd_principal_pv = 0.0

        for i in range(n_periods):
            period_start = dates[i]
            period_end = dates[i + 1]
            not_usd_i = notional_usd * remaining[i]
            not_cop_i = notional_cop * remaining[i]
            period_is_past = period_end <= curve_ref

            if period_is_past:
                periods.append(None)
                continue

            fwd_start = max(period_start, curve_ref)
            if fwd_start >= period_end:
                usd_fwd = 0.0
                cop_fwd = 0.0
            else:
                usd_fwd = self.cm.sofr_handle.forwardRate(
                    fwd_start, period_end, day_counter, ql.Simple
                ).rate()
                cop_fwd = self.cm.ibr_handle.forwardRate(
                    fwd_start, period_end, day_counter, ql.Simple
                ).rate()

            usd_df = self.cm.sofr_handle.discount(period_end)
            cop_df = self.cm.ibr_handle.discount(period_end)
            tau = day_counter.yearFraction(period_start, period_end)

            # COP interest (invariant — doesn't depend on USD spread)
            cop_interest = not_cop_i * (cop_fwd + cop_spread) * tau
            cop_interest_pv += cop_interest * cop_df

            # Principal PVs (invariant)
            usd_principal = notional_usd * amort_pcts[i]
            cop_principal = notional_cop * amort_pcts[i]
            usd_principal_pv += usd_principal * usd_df
            cop_principal_pv += cop_principal * cop_df

            # Store what varies with USD spread
            periods.append({
                "not_usd_i": not_usd_i,
                "usd_fwd": usd_fwd,
                "tau": tau,
                "usd_df": usd_df,
            })

        return {
            "periods": periods,
            "cop_interest_pv": cop_interest_pv,
            "cop_principal_pv": cop_principal_pv,
            "usd_principal_pv": usd_principal_pv,
            "sign": sign,
            "spot": spot,
            "fx": fx,
        }

    def _fast_npv(self, precomputed: dict, usd_spread_bps: float) -> float:
        """Compute NPV using pre-computed period data. Only varies USD spread."""
        usd_spread = usd_spread_bps / 10000.0
        usd_interest_pv = 0.0
        for p in precomputed["periods"]:
            if p is None:
                continue
            usd_interest = p["not_usd_i"] * (p["usd_fwd"] + usd_spread) * p["tau"]
            usd_interest_pv += usd_interest * p["usd_df"]

        usd_total_pv = usd_interest_pv + precomputed["usd_principal_pv"]
        cop_total_pv = precomputed["cop_interest_pv"] + precomputed["cop_principal_pv"]
        return precomputed["sign"] * (cop_total_pv - usd_total_pv * precomputed["spot"])

    def _par_xccy_basis_internal(
        self,
        notional_usd: float,
        start_date,
        maturity_date,
        cop_spread_bps: float = 0.0,
        pay_usd: bool = True,
        fx_initial: float = None,
        payment_frequency: str = "3M",
        amortization_type: str = "bullet",
        amortization_schedule: list = None,
    ) -> float:
        """Find the par xccy basis spread (bps) on the USD leg that makes NPV = 0."""
        pre = self._precompute_periods(
            notional_usd, start_date, maturity_date,
            cop_spread_bps, pay_usd, fx_initial,
            payment_frequency, amortization_type, amortization_schedule,
        )
        return brentq(lambda bps: self._fast_npv(pre, bps), -500, 500, xtol=0.5)

    def par_xccy_basis(
        self,
        notional_usd: float,
        start_date,
        maturity_date,
        fx_initial: float = None,
        payment_frequency: str = "3M",
        amortization_type: str = "bullet",
        amortization_schedule: list = None,
    ) -> float:
        """
        Find the par cross-currency basis spread (bps on USD leg) that makes NPV = 0.

        Returns:
            Par xccy basis spread in bps
        """
        return self._par_xccy_basis_internal(
            notional_usd=notional_usd,
            start_date=start_date,
            maturity_date=maturity_date,
            cop_spread_bps=0.0,
            pay_usd=True,
            fx_initial=fx_initial,
            payment_frequency=payment_frequency,
            amortization_type=amortization_type,
            amortization_schedule=amortization_schedule,
        )

    def par_basis_curve(
        self,
        notional_usd: float = 1_000_000,
        fx_initial: float = None,
        payment_frequency: str = "3M",
        amortization_type: str = "bullet",
        tenors_years: list = None,
    ) -> list:
        """
        Compute par xccy basis for standard tenors.

        Args:
            tenors_years: List of tenors in years (default: [1, 2, 3, 5, 7, 10])

        Returns:
            List of dicts with tenor, tenor_years, par_basis_bps
        """
        if tenors_years is None:
            tenors_years = [1, 2, 3, 5, 7, 10]

        cop_cal = self.cm.ibr_index.fixingCalendar()
        usd_cal = self.cm.sofr_index.fixingCalendar()
        joint_cal = ql.JointCalendar(cop_cal, usd_cal)

        start_date = joint_cal.advance(
            self.cm.valuation_date, ql.Period(2, ql.Days)
        )

        results = []
        for years in tenors_years:
            mat = joint_cal.advance(start_date, ql.Period(years, ql.Years))
            try:
                basis = self.par_xccy_basis(
                    notional_usd=notional_usd,
                    start_date=start_date,
                    maturity_date=mat,
                    fx_initial=fx_initial,
                    payment_frequency=payment_frequency,
                    amortization_type=amortization_type,
                )
                results.append({
                    "tenor": f"{years}Y",
                    "tenor_years": years,
                    "par_basis_bps": round(basis, 2),
                })
            except Exception as e:
                results.append({
                    "tenor": f"{years}Y",
                    "tenor_years": years,
                    "par_basis_bps": None,
                    "error": str(e),
                })
        return results

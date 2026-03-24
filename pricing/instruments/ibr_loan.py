"""
IBR Variable-Rate Loan pricer.

Prices Colombian loans indexed to IBR (Indicador Bancario de Referencia)
using the CurveManager infrastructure for forward rate projection and
discounting.

Structure:
  - Rate: IBR (from curve forward rates) + client spread
  - Day count: Configurable (30/360, Actual/365, per-period)
  - Amortization: French (annuity), linear, or bullet
  - Grace periods: capital, interest, or both (ambos)
  - Rates are nominal (annual nominal / periods_per_year)

Conventions:
  - Interest rates entered as nominal annual in percent (e.g., 12.0 = 12%)
  - Spread is additive over IBR in percent (e.g., 3.5 = 3.5%)
  - min_period_rate is a floor on (IBR + spread) in percent
  - Forward IBR rates are extracted from CurveManager.ibr_handle

Integration:
  - Uses CurveManager for curve access (same pattern as XccySwapPricer)
  - Settled periods use historical rates from db_info
  - Future periods use forward rates from the IBR curve
"""
import QuantLib as ql
import pandas as pd
from datetime import datetime
from utilities.date_functions import datetime_to_ql, ql_to_datetime
from utilities.colombia_calendar import calendar_colombia


# Periodicity mappings
PERIODICITY_MONTHS = {
    "Anual": 12,
    "Semestral": 6,
    "Trimestral": 3,
    "Bimensual": 2,
    "Mensual": 1,
}

PERIODICITY_FRACTION = {
    "Anual": 1.0,
    "Semestral": 0.5,
    "Trimestral": 0.25,
    "Bimensual": 1 / 6,
    "Mensual": 1 / 12,
}

# IBR tenor key per periodicity (for historical lookups in db_info)
PERIODICITY_IBR_KEY = {
    "Anual": "ibr_12m",
    "Semestral": "ibr_6m",
    "Trimestral": "ibr_3m",
    "Bimensual": "ibr_2m",
    "Mensual": "ibr_1m",
}

# Day count conventions
DAY_COUNT_MAP = {
    "por_dias_360": ql.Thirty360(ql.Thirty360.BondBasis),
    "por_dias_365": ql.Actual365Fixed(),
    "por_periodo": None,  # handled separately
}

DAY_COUNT_DIVISOR = {
    "por_dias_360": 360,
    "por_dias_365": 365,
}

# Amortization types
AMORTIZATION_TYPES = ("french", "linear", "bullet")

# Grace types
GRACE_TYPES = (None, "capital", "interest", "ambos")


class IbrLoanPricer:
    """
    Prices IBR variable-rate loans using the CurveManager infrastructure.

    Requires CurveManager with IBR curve built.
    """

    def __init__(self, curve_manager):
        self.cm = curve_manager
        self.calendar = calendar_colombia()

    def _build_schedule(self, start_date, maturity_date, periodicity):
        """Build payment schedule from start to maturity."""
        period = ql.Period(PERIODICITY_MONTHS[periodicity], ql.Months)
        schedule = ql.Schedule(
            start_date, maturity_date,
            period,
            self.calendar,
            ql.Following, ql.Following,
            ql.DateGeneration.Forward, False,
        )
        return schedule

    def _build_notionals(
        self,
        n_periods,
        notional,
        amortization_type,
        grace_period_principal,
    ):
        """
        Build per-period notional (beginning balance) and principal payment arrays.

        Returns:
            (beginning_balances, principal_payments) — lists of length n_periods
        """
        capital_periods = n_periods - int(grace_period_principal)

        if amortization_type == "bullet":
            # No principal until maturity
            principals = [0.0] * (n_periods - 1) + [notional]
            balances = [notional] * n_periods

        elif amortization_type == "linear":
            if capital_periods <= 0:
                raise ValueError(
                    f"Grace period ({grace_period_principal}) >= total periods ({n_periods})"
                )
            capital_payment = notional / capital_periods
            principals = []
            balances = []
            balance = notional
            for i in range(n_periods):
                balances.append(balance)
                if i < grace_period_principal:
                    principals.append(0.0)
                else:
                    principals.append(capital_payment)
                    balance -= capital_payment
            # Fix rounding on last period
            if abs(balance) < 1e-2:
                balance = 0.0

        elif amortization_type == "french":
            if capital_periods <= 0:
                raise ValueError(
                    f"Grace period ({grace_period_principal}) >= total periods ({n_periods})"
                )
            # French amortization requires knowing the rate for each period,
            # which depends on forward rates. We handle this in the cashflow
            # generation loop instead. Return placeholder here.
            principals = None
            balances = None

        else:
            raise ValueError(
                f"Unknown amortization_type '{amortization_type}'. "
                f"Valid: {AMORTIZATION_TYPES}"
            )

        return balances, principals

    def _get_ibr_rate(
        self,
        period_start,
        period_end,
        periodicity,
        db_info=None,
        historical_rates=None,
    ):
        """
        Get the IBR rate for a period.

        For settled periods (period_start < valuation_date): looks up historical
        rate from db_info DataFrame.

        For future periods: extracts forward rate from the IBR curve.

        Returns:
            IBR rate as decimal (e.g., 0.095 for 9.5%)
        """
        eval_date = ql.Settings.instance().evaluationDate
        ibr_ref = self.cm.ibr_handle.currentLink().referenceDate()
        curve_floor = max(eval_date, ibr_ref)

        if period_start < curve_floor and historical_rates is not None:
            # Settled period — use historical rate
            ibr_key = PERIODICITY_IBR_KEY[periodicity]
            p_start_dt = ql_to_datetime(period_start)
            # Find closest date in historical data
            hist_df = historical_rates
            if not hist_df.empty:
                idx = hist_df["date"].sub(pd.Timestamp(p_start_dt)).abs().idxmin()
                rate_pct = hist_df.at[idx, ibr_key]
                if rate_pct is not None:
                    return rate_pct / 100.0
            # Fallback to curve if no historical data
            return None

        # Future period — use forward rate from curve
        fwd_start = period_start if period_start >= ibr_ref else ibr_ref
        fwd_rate = self.cm.ibr_handle.forwardRate(
            fwd_start, period_end, ql.Actual360(), ql.Simple
        ).rate()
        return fwd_rate

    def _compute_interest_factor(
        self,
        rate_total_pct,
        period_start,
        period_end,
        days_count,
        periodicity,
    ):
        """
        Compute the interest factor for a period given the total rate and convention.

        Args:
            rate_total_pct: Total rate (IBR + spread) in percent
            period_start: QL date — start of the accrual period
            period_end: QL date — end of the accrual period
            days_count: Day count convention string
            periodicity: Payment periodicity string

        Returns:
            Interest factor as decimal (multiply by balance to get interest amount)
        """
        rate_decimal = rate_total_pct / 100.0

        if days_count == "por_periodo":
            # Nominal rate → periodic rate: annual_nominal * period_fraction
            period_fraction = PERIODICITY_FRACTION[periodicity]
            return rate_decimal * period_fraction

        # Day-count based: actual_days * rate / divisor
        dc = DAY_COUNT_MAP[days_count]
        days = dc.dayCount(period_start, period_end)
        divisor = DAY_COUNT_DIVISOR[days_count]
        return days * rate_decimal / divisor

    def _prepare_historical_rates(self, db_info):
        """Prepare historical rates DataFrame from db_info dict."""
        if db_info is None:
            return None
        df = pd.DataFrame(db_info)
        if "fecha" in df.columns:
            df["date"] = pd.to_datetime(df["fecha"])
        elif "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        else:
            return None
        return df

    def cashflows(
        self,
        notional: float,
        start_date,
        maturity_date,
        spread_pct: float,
        periodicity: str = "Trimestral",
        days_count: str = "por_dias_360",
        amortization_type: str = "linear",
        grace_type: str = None,
        grace_period: int = 0,
        min_period_rate: float = None,
        db_info: dict = None,
    ) -> list:
        """
        Full cashflow schedule for an IBR variable-rate loan.

        Returns one dict per period with: date, balance, IBR rate, spread,
        total rate, interest, principal, payment, discount factor, PV, status.

        For settled periods, uses historical IBR rates from db_info.
        For future periods, uses forward rates from the IBR curve.

        Args:
            notional: Original loan amount (COP)
            start_date: Loan origination date
            maturity_date: Final payment date
            spread_pct: Client spread over IBR in percent (e.g., 3.5)
            periodicity: Payment frequency
            days_count: Day count convention
            amortization_type: 'french', 'linear', or 'bullet'
            grace_type: None, 'capital', 'interest', or 'ambos'
            grace_period: Number of grace periods
            min_period_rate: Floor on total rate (IBR + spread) in percent
            db_info: Historical IBR rates dict (from Supabase)

        Returns:
            List of dicts, one per period
        """
        if isinstance(start_date, datetime):
            start_date = datetime_to_ql(start_date)
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        # Validate inputs
        if periodicity not in PERIODICITY_MONTHS:
            raise ValueError(f"Invalid periodicity '{periodicity}'. Valid: {list(PERIODICITY_MONTHS.keys())}")
        if days_count not in DAY_COUNT_MAP:
            raise ValueError(f"Invalid days_count '{days_count}'. Valid: {list(DAY_COUNT_MAP.keys())}")
        if amortization_type not in AMORTIZATION_TYPES:
            raise ValueError(f"Invalid amortization_type '{amortization_type}'. Valid: {list(AMORTIZATION_TYPES)}")
        if grace_type not in GRACE_TYPES:
            raise ValueError(f"Invalid grace_type '{grace_type}'. Valid: {list(GRACE_TYPES)}")

        grace_period = int(grace_period) if grace_period else 0
        grace_period_principal = grace_period if grace_type in ("capital", "ambos") else 0
        grace_period_interest = grace_period if grace_type in ("interest", "ambos") else 0

        schedule = self._build_schedule(start_date, maturity_date, periodicity)
        dates = list(schedule)
        n_periods = len(dates) - 1

        if n_periods <= 0:
            raise ValueError("Schedule has no periods. Check start_date and maturity_date.")

        capital_periods = n_periods - grace_period_principal
        if capital_periods <= 0:
            raise ValueError(
                f"Grace period ({grace_period_principal}) >= total periods ({n_periods})"
            )

        historical_rates = self._prepare_historical_rates(db_info)
        eval_date = ql.Settings.instance().evaluationDate
        ibr_ref = self.cm.ibr_handle.currentLink().referenceDate()

        rows = []
        balance = notional
        accumulated_interest = 0.0  # For grace periods with capitalization

        for i in range(n_periods):
            p_start = dates[i]
            p_end = dates[i + 1]

            # Determine period status
            if p_end <= eval_date:
                status = "settled"
            elif p_start < eval_date:
                status = "current"
            else:
                status = "future"

            # Get IBR rate for this period
            ibr_rate = self._get_ibr_rate(
                p_start, p_end, periodicity,
                historical_rates=historical_rates,
            )

            if ibr_rate is None:
                # No historical data, no curve — skip or use 0
                ibr_rate_pct = 0.0
            else:
                ibr_rate_pct = ibr_rate * 100.0

            # Total rate = IBR + spread, floored by min_period_rate
            rate_total_pct = ibr_rate_pct + spread_pct
            if min_period_rate is not None:
                rate_total_pct = max(rate_total_pct, min_period_rate)

            # Interest calculation
            interest_factor = self._compute_interest_factor(
                rate_total_pct, p_start, p_end, days_count, periodicity,
            )

            if i < grace_period_interest:
                # Grace on interest: no payment, interest capitalizes
                interest_amount = 0.0
                accumulated_interest += balance * interest_factor
            else:
                # If exiting interest grace, add capitalized interest to balance
                if accumulated_interest > 0 and i == grace_period_interest:
                    balance += accumulated_interest
                    accumulated_interest = 0.0
                interest_amount = balance * interest_factor

            # Principal calculation
            if i < grace_period_principal:
                principal_amount = 0.0
            else:
                if amortization_type == "linear":
                    principal_amount = notional / capital_periods
                    # Adjust last period for rounding
                    if i == n_periods - 1:
                        principal_amount = balance
                elif amortization_type == "bullet":
                    principal_amount = balance if i == n_periods - 1 else 0.0
                elif amortization_type == "french":
                    # Recalculate annuity payment based on current balance and rate
                    remaining_periods = n_periods - i
                    period_rate = interest_factor
                    if abs(period_rate) < 1e-10:
                        annuity = balance / remaining_periods
                    else:
                        annuity = balance * period_rate / (1 - (1 + period_rate) ** (-remaining_periods))
                    principal_amount = annuity - interest_amount

            payment = interest_amount + principal_amount
            ending_balance = balance - principal_amount

            # Discount factor for PV calculation
            if p_end > ibr_ref:
                df = self.cm.ibr_handle.discount(p_end)
            else:
                df = 1.0  # Settled periods

            pv = payment * df

            rows.append({
                "period": i + 1,
                "date_start": ql_to_datetime(p_start).strftime("%Y-%m-%d"),
                "date_end": ql_to_datetime(p_end).strftime("%Y-%m-%d"),
                "beginning_balance": round(balance, 2),
                "ibr_rate_pct": round(ibr_rate_pct, 6),
                "spread_pct": spread_pct,
                "rate_total_pct": round(rate_total_pct, 6),
                "interest": round(interest_amount, 2),
                "principal": round(principal_amount, 2),
                "payment": round(payment, 2),
                "ending_balance": round(ending_balance, 2),
                "discount_factor": round(df, 8),
                "pv": round(pv, 2),
                "status": status,
            })

            balance = ending_balance

        return rows

    def price(
        self,
        notional: float,
        start_date,
        maturity_date,
        spread_pct: float,
        periodicity: str = "Trimestral",
        days_count: str = "por_dias_360",
        amortization_type: str = "linear",
        grace_type: str = None,
        grace_period: int = 0,
        min_period_rate: float = None,
        db_info: dict = None,
    ) -> dict:
        """
        Price an IBR variable-rate loan and return analytics.

        Returns:
            dict with: npv, notional, spread_pct, irr, duration, tenor_years,
                       accrued_interest, principal_outstanding, periods_total,
                       periods_remaining
        """
        cfs = self.cashflows(
            notional=notional,
            start_date=start_date,
            maturity_date=maturity_date,
            spread_pct=spread_pct,
            periodicity=periodicity,
            days_count=days_count,
            amortization_type=amortization_type,
            grace_type=grace_type,
            grace_period=grace_period,
            min_period_rate=min_period_rate,
            db_info=db_info,
        )

        # NPV: sum of PV of all future cashflows
        future_cfs = [cf for cf in cfs if cf["status"] != "settled"]
        npv = sum(cf["pv"] for cf in future_cfs)

        # Principal outstanding
        if future_cfs:
            principal_outstanding = future_cfs[0]["beginning_balance"]
        else:
            principal_outstanding = 0.0

        # Accrued interest for current period
        accrued_interest = 0.0
        eval_date = ql.Settings.instance().evaluationDate
        for cf in cfs:
            if cf["status"] == "current":
                p_start = datetime_to_ql(datetime.strptime(cf["date_start"], "%Y-%m-%d"))
                p_end = datetime_to_ql(datetime.strptime(cf["date_end"], "%Y-%m-%d"))
                dc = ql.Actual365Fixed()
                total_days = dc.dayCount(p_start, p_end)
                elapsed_days = dc.dayCount(p_start, eval_date)
                if total_days > 0:
                    accrued_interest = cf["interest"] * elapsed_days / total_days
                break

        # Duration (Macaulay) — weighted average time of future cashflows
        total_pv = sum(cf["pv"] for cf in future_cfs) if future_cfs else 0.0
        eval_dt = ql_to_datetime(eval_date)
        duration = 0.0
        if total_pv > 0:
            for cf in future_cfs:
                cf_date = datetime.strptime(cf["date_end"], "%Y-%m-%d")
                t_years = (cf_date - eval_dt).days / 365.25
                duration += t_years * cf["pv"] / total_pv

        # Tenor
        if cfs:
            last_date = datetime.strptime(cfs[-1]["date_end"], "%Y-%m-%d")
            tenor_years = (last_date - eval_dt).days / 365.25
        else:
            tenor_years = 0.0

        # Periods info
        periods_total = len(cfs)
        periods_remaining = len(future_cfs)

        # Weighted average rate (future periods only)
        if future_cfs:
            total_balance = sum(cf["beginning_balance"] for cf in future_cfs)
            if total_balance > 0:
                avg_rate = sum(
                    cf["rate_total_pct"] * cf["beginning_balance"] for cf in future_cfs
                ) / total_balance
            else:
                avg_rate = 0.0
        else:
            avg_rate = 0.0

        return {
            "npv": round(npv, 2),
            "notional": notional,
            "spread_pct": spread_pct,
            "principal_outstanding": round(principal_outstanding, 2),
            "accrued_interest": round(accrued_interest, 2),
            "total_value": round(principal_outstanding + accrued_interest, 2),
            "duration": round(duration, 4),
            "tenor_years": round(tenor_years, 4),
            "avg_rate_pct": round(avg_rate, 4),
            "periods_total": periods_total,
            "periods_remaining": periods_remaining,
            "amortization_type": amortization_type,
            "periodicity": periodicity,
            "days_count": days_count,
        }

    def par_spread(
        self,
        notional: float,
        start_date,
        maturity_date,
        periodicity: str = "Trimestral",
        days_count: str = "por_dias_360",
        amortization_type: str = "linear",
        grace_type: str = None,
        grace_period: int = 0,
        min_period_rate: float = None,
        db_info: dict = None,
    ) -> float:
        """
        Find the spread over IBR that makes NPV = notional (fair spread).

        Returns:
            Par spread in percent
        """
        from scipy.optimize import brentq

        def objective(spread):
            result = self.price(
                notional=notional,
                start_date=start_date,
                maturity_date=maturity_date,
                spread_pct=spread,
                periodicity=periodicity,
                days_count=days_count,
                amortization_type=amortization_type,
                grace_type=grace_type,
                grace_period=grace_period,
                min_period_rate=min_period_rate,
                db_info=db_info,
            )
            return result["npv"] - notional

        par = brentq(objective, -50.0, 50.0, xtol=0.0001)
        return round(par, 4)

    def dv01(
        self,
        notional: float,
        start_date,
        maturity_date,
        spread_pct: float,
        periodicity: str = "Trimestral",
        days_count: str = "por_dias_360",
        amortization_type: str = "linear",
        grace_type: str = None,
        grace_period: int = 0,
        min_period_rate: float = None,
        db_info: dict = None,
        bump_bps: float = 1.0,
    ) -> dict:
        """
        Compute DV01 (rate sensitivity) for the loan.

        Bumps the IBR curve by bump_bps and measures NPV change.

        Returns:
            dict with dv01_cop, bump_bps, base_npv, bumped_npv
        """
        common_args = dict(
            notional=notional,
            start_date=start_date,
            maturity_date=maturity_date,
            spread_pct=spread_pct,
            periodicity=periodicity,
            days_count=days_count,
            amortization_type=amortization_type,
            grace_type=grace_type,
            grace_period=grace_period,
            min_period_rate=min_period_rate,
            db_info=db_info,
        )

        base = self.price(**common_args)
        base_npv = base["npv"]

        self.cm.bump_ibr(bump_bps)
        bumped = self.price(**common_args)
        bumped_npv = bumped["npv"]
        self.cm.bump_ibr(-bump_bps)

        return {
            "dv01_cop": round(bumped_npv - base_npv, 2),
            "bump_bps": bump_bps,
            "base_npv": base_npv,
            "bumped_npv": bumped_npv,
        }

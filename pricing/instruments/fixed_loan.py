"""
Fixed-Rate Loan pricer.

Prices Colombian fixed-rate loans using the CurveManager infrastructure
for discounting future cashflows with the IBR curve.

Structure:
  - Rate: Fixed nominal annual rate
  - Day count: Configurable (30/360, Actual/365, per-period)
  - Amortization: French (annuity), linear, or bullet
  - Grace periods: capital, interest, or both (ambos)
  - Rates are nominal (annual nominal / periods_per_year)

Integration:
  - Uses CurveManager.ibr_handle for discounting (market-implied rates)
  - All periods have the same known rate (no forward projection needed)
  - NPV = sum of discounted future cashflows
"""
import QuantLib as ql
from datetime import datetime
from utilities.date_functions import datetime_to_ql, ql_to_datetime
from utilities.colombia_calendar import calendar_colombia
from pricing.instruments.ibr_loan import (
    PERIODICITY_MONTHS,
    PERIODICITY_FRACTION,
    DAY_COUNT_MAP,
    DAY_COUNT_DIVISOR,
    AMORTIZATION_TYPES,
    GRACE_TYPES,
)


class FixedLoanPricer:
    """
    Prices fixed-rate loans using the CurveManager for discounting.

    Requires CurveManager with IBR curve built (used for discounting only).
    """

    def __init__(self, curve_manager):
        self.cm = curve_manager
        self.calendar = calendar_colombia()

    def _build_schedule(self, start_date, maturity_date, periodicity):
        """Build payment schedule from start to maturity."""
        period = ql.Period(PERIODICITY_MONTHS[periodicity], ql.Months)
        return ql.Schedule(
            start_date, maturity_date,
            period,
            self.calendar,
            ql.Following, ql.Following,
            ql.DateGeneration.Forward, False,
        )

    def _compute_interest_factor(
        self, rate_pct, period_start, period_end, days_count, periodicity,
    ):
        """
        Compute the interest factor for a period.

        Returns:
            Interest factor as decimal (multiply by balance to get interest)
        """
        rate_decimal = rate_pct / 100.0

        if days_count == "por_periodo":
            return rate_decimal * PERIODICITY_FRACTION[periodicity]

        dc = DAY_COUNT_MAP[days_count]
        days = dc.dayCount(period_start, period_end)
        divisor = DAY_COUNT_DIVISOR[days_count]
        return days * rate_decimal / divisor

    def cashflows(
        self,
        notional: float,
        start_date,
        maturity_date,
        rate_pct: float,
        periodicity: str = "Mensual",
        days_count: str = "por_dias_360",
        amortization_type: str = "french",
        grace_type: str = None,
        grace_period: int = 0,
    ) -> list:
        """
        Full cashflow schedule for a fixed-rate loan.

        Args:
            notional: Original loan amount (COP)
            start_date: Loan origination date
            maturity_date: Final payment date
            rate_pct: Annual nominal interest rate in percent (e.g., 12.0)
            periodicity: Payment frequency
            days_count: Day count convention
            amortization_type: 'french', 'linear', or 'bullet'
            grace_type: None, 'capital', 'interest', or 'ambos'
            grace_period: Number of grace periods

        Returns:
            List of dicts, one per period
        """
        if isinstance(start_date, datetime):
            start_date = datetime_to_ql(start_date)
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        if periodicity not in PERIODICITY_MONTHS:
            raise ValueError(f"Invalid periodicity '{periodicity}'. Valid: {list(PERIODICITY_MONTHS.keys())}")
        if days_count not in DAY_COUNT_MAP:
            raise ValueError(f"Invalid days_count '{days_count}'. Valid: {list(DAY_COUNT_MAP.keys())}")
        if amortization_type not in AMORTIZATION_TYPES:
            raise ValueError(f"Invalid amortization_type. Valid: {list(AMORTIZATION_TYPES)}")
        if grace_type not in GRACE_TYPES:
            raise ValueError(f"Invalid grace_type. Valid: {list(GRACE_TYPES)}")

        grace_period = int(grace_period) if grace_period else 0
        grace_period_principal = grace_period if grace_type in ("capital", "ambos") else 0
        grace_period_interest = grace_period if grace_type in ("interest", "ambos") else 0

        schedule = self._build_schedule(start_date, maturity_date, periodicity)
        dates = list(schedule)
        n_periods = len(dates) - 1

        if n_periods <= 0:
            raise ValueError("Schedule has no periods.")

        capital_periods = n_periods - grace_period_principal
        if capital_periods <= 0:
            raise ValueError(f"Grace period ({grace_period_principal}) >= total periods ({n_periods})")

        eval_date = ql.Settings.instance().evaluationDate
        ibr_ref = self.cm.ibr_handle.currentLink().referenceDate()

        # For french amortization, calculate the fixed annuity payment
        # (computed once, valid for all capital periods with same rate)
        if amortization_type == "french":
            period_rate = self._compute_interest_factor(
                rate_pct, dates[0], dates[1], days_count, periodicity,
            )
            if abs(period_rate) < 1e-10:
                annuity_payment = notional / capital_periods
            else:
                annuity_payment = notional * period_rate / (
                    1 - (1 + period_rate) ** (-capital_periods)
                )

        rows = []
        balance = notional
        accumulated_interest = 0.0

        for i in range(n_periods):
            p_start = dates[i]
            p_end = dates[i + 1]

            if p_end <= eval_date:
                status = "settled"
            elif p_start < eval_date:
                status = "current"
            else:
                status = "future"

            interest_factor = self._compute_interest_factor(
                rate_pct, p_start, p_end, days_count, periodicity,
            )

            # Interest
            if i < grace_period_interest:
                interest_amount = 0.0
                accumulated_interest += balance * interest_factor
            else:
                if accumulated_interest > 0 and i == grace_period_interest:
                    balance += accumulated_interest
                    accumulated_interest = 0.0
                interest_amount = balance * interest_factor

            # Principal
            if i < grace_period_principal:
                principal_amount = 0.0
            else:
                if amortization_type == "linear":
                    principal_amount = notional / capital_periods
                    if i == n_periods - 1:
                        principal_amount = balance
                elif amortization_type == "bullet":
                    principal_amount = balance if i == n_periods - 1 else 0.0
                elif amortization_type == "french":
                    principal_amount = annuity_payment - interest_amount
                    if i == n_periods - 1:
                        principal_amount = balance  # Clean up rounding

            payment = interest_amount + principal_amount
            ending_balance = balance - principal_amount

            # Discount factor
            if p_end > ibr_ref:
                df = self.cm.ibr_handle.discount(p_end)
            else:
                df = 1.0

            pv = payment * df

            rows.append({
                "period": i + 1,
                "date_start": ql_to_datetime(p_start).strftime("%Y-%m-%d"),
                "date_end": ql_to_datetime(p_end).strftime("%Y-%m-%d"),
                "beginning_balance": round(balance, 2),
                "rate_pct": rate_pct,
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
        rate_pct: float,
        periodicity: str = "Mensual",
        days_count: str = "por_dias_360",
        amortization_type: str = "french",
        grace_type: str = None,
        grace_period: int = 0,
    ) -> dict:
        """
        Price a fixed-rate loan and return analytics.

        Returns:
            dict with: npv, notional, rate_pct, principal_outstanding,
                       accrued_interest, total_value, duration, tenor_years,
                       periods_total, periods_remaining
        """
        cfs = self.cashflows(
            notional=notional,
            start_date=start_date,
            maturity_date=maturity_date,
            rate_pct=rate_pct,
            periodicity=periodicity,
            days_count=days_count,
            amortization_type=amortization_type,
            grace_type=grace_type,
            grace_period=grace_period,
        )

        future_cfs = [cf for cf in cfs if cf["status"] != "settled"]
        npv = sum(cf["pv"] for cf in future_cfs)

        principal_outstanding = future_cfs[0]["beginning_balance"] if future_cfs else 0.0

        # Accrued interest
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

        # Duration (Macaulay)
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

        return {
            "npv": round(npv, 2),
            "notional": notional,
            "rate_pct": rate_pct,
            "principal_outstanding": round(principal_outstanding, 2),
            "accrued_interest": round(accrued_interest, 2),
            "total_value": round(principal_outstanding + accrued_interest, 2),
            "duration": round(duration, 4),
            "tenor_years": round(tenor_years, 4),
            "periods_total": len(cfs),
            "periods_remaining": len(future_cfs),
            "amortization_type": amortization_type,
            "periodicity": periodicity,
            "days_count": days_count,
        }

    def dv01(
        self,
        notional: float,
        start_date,
        maturity_date,
        rate_pct: float,
        periodicity: str = "Mensual",
        days_count: str = "por_dias_360",
        amortization_type: str = "french",
        grace_type: str = None,
        grace_period: int = 0,
        bump_bps: float = 1.0,
    ) -> dict:
        """
        DV01: sensitivity of NPV to a 1bp parallel shift in the IBR discount curve.

        Note: This bumps the DISCOUNT curve, not the loan's fixed rate.
        It measures how much the market value of the loan changes when
        market rates move, holding the loan's contractual rate fixed.
        """
        common_args = dict(
            notional=notional,
            start_date=start_date,
            maturity_date=maturity_date,
            rate_pct=rate_pct,
            periodicity=periodicity,
            days_count=days_count,
            amortization_type=amortization_type,
            grace_type=grace_type,
            grace_period=grace_period,
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

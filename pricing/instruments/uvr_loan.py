"""
UVR-Indexed Loan pricer.

Prices Colombian UVR (Unidad de Valor Real) loans using the CurveManager
infrastructure for discounting.

Structure:
  - Loan is denominated in UVR units
  - Rate: Fixed nominal annual over UVR (real rate)
  - Cashflows in UVR are converted to COP using UVR values at each date
  - For future dates, UVR is projected using the inflation breakeven
    (TES COP yield - TES UVR yield) or a flat assumption

Day count, amortization, and grace period handling follow the same
conventions as FixedLoanPricer.

Integration:
  - Uses CurveManager.ibr_handle for COP discounting
  - Historical UVR values from db_info (banrep UVR series)
  - Future UVR projected from last known value + inflation assumption
"""
import QuantLib as ql
import pandas as pd
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


class UvrLoanPricer:
    """
    Prices UVR-indexed loans using the CurveManager for discounting.

    Loan is originated in UVR units. All cashflows are computed in UVR
    and then converted to COP using historical or projected UVR values.

    Requires CurveManager with IBR curve built (for COP discounting).
    """

    def __init__(self, curve_manager):
        self.cm = curve_manager
        self.calendar = calendar_colombia()

    def _build_schedule(self, start_date, maturity_date, periodicity):
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
        rate_decimal = rate_pct / 100.0
        if days_count == "por_periodo":
            return rate_decimal * PERIODICITY_FRACTION[periodicity]
        dc = DAY_COUNT_MAP[days_count]
        days = dc.dayCount(period_start, period_end)
        divisor = DAY_COUNT_DIVISOR[days_count]
        return days * rate_decimal / divisor

    def _get_uvr_value(
        self, date_ql, uvr_hist_df, uvr_proj_df=None,
        inflation_annual=None, last_known_uvr=None, last_known_date=None,
    ):
        """
        Get UVR value for a date.

        Lookup priority:
          1. uvr_hist_df — historical UVR from banrep_series_value_v2 (nearest within 5 days)
          2. uvr_proj_df — projected UVR from uvr_projection table (nearest within 5 days)
          3. Flat inflation fallback — projects from last known UVR using inflation_annual

        Args:
            date_ql: QuantLib date
            uvr_hist_df: DataFrame with columns 'date' and 'valor' (historical)
            uvr_proj_df: DataFrame with columns 'date' and 'valor' (projected, from uvr_projection)
            inflation_annual: Annual inflation rate for flat fallback (decimal, e.g. 0.05)
            last_known_uvr: Last observed UVR value
            last_known_date: Date of last observation (datetime)

        Returns:
            UVR value as float
        """
        date_dt = ql_to_datetime(date_ql)
        date_ts = pd.Timestamp(date_dt)

        # Priority 1: Historical UVR
        if uvr_hist_df is not None and not uvr_hist_df.empty:
            closest_idx = uvr_hist_df["date"].sub(date_ts).abs().idxmin()
            closest_date = uvr_hist_df.at[closest_idx, "date"]
            if abs((closest_date - date_ts).days) <= 5:
                return uvr_hist_df.at[closest_idx, "valor"]

        # Priority 2: Projected UVR (from uvr_projection table)
        if uvr_proj_df is not None and not uvr_proj_df.empty:
            closest_idx = uvr_proj_df["date"].sub(date_ts).abs().idxmin()
            closest_date = uvr_proj_df.at[closest_idx, "date"]
            if abs((closest_date - date_ts).days) <= 5:
                return uvr_proj_df.at[closest_idx, "valor"]

        # Priority 3: Flat inflation fallback
        if last_known_uvr is not None and last_known_date is not None and inflation_annual is not None:
            days_ahead = (date_dt - last_known_date).days
            if days_ahead > 0:
                daily_rate = (1 + inflation_annual) ** (1 / 365) - 1
                return last_known_uvr * (1 + daily_rate) ** days_ahead

        # Fallback: return 1.0 (UVR units = COP units, no conversion)
        return 1.0

    def _prepare_uvr_data(self, db_info):
        """Prepare UVR DataFrame from db_info (historical or projected)."""
        if db_info is None:
            return None, None, None
        df = pd.DataFrame(db_info) if not isinstance(db_info, pd.DataFrame) else db_info.copy()
        if "fecha" in df.columns:
            df["date"] = pd.to_datetime(df["fecha"])
        elif "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        else:
            return None, None, None

        if "valor" not in df.columns:
            return None, None, None

        df = df.sort_values("date").reset_index(drop=True)
        last_known_uvr = float(df["valor"].iloc[-1])
        last_known_date = df["date"].iloc[-1].to_pydatetime()
        return df, last_known_uvr, last_known_date

    def cashflows(
        self,
        notional_uvr: float,
        start_date,
        maturity_date,
        rate_pct: float,
        periodicity: str = "Mensual",
        days_count: str = "por_dias_360",
        amortization_type: str = "french",
        grace_type: str = None,
        grace_period: int = 0,
        db_info: dict = None,
        uvr_projection: dict = None,
        inflation_annual: float = 0.05,
    ) -> list:
        """
        Full cashflow schedule for a UVR-indexed loan.

        All calculations are done in UVR units first, then converted to COP.

        Args:
            notional_uvr: Original loan amount in UVR units
            start_date: Loan origination date
            maturity_date: Final payment date
            rate_pct: Annual nominal real rate in percent (e.g., 7.0)
            periodicity: Payment frequency
            days_count: Day count convention
            amortization_type: 'french', 'linear', or 'bullet'
            grace_type: None, 'capital', 'interest', or 'ambos'
            grace_period: Number of grace periods
            db_info: Historical UVR values (columns: fecha, valor) from banrep_series_value_v2
            uvr_projection: Projected UVR values (columns: fecha, valor) from uvr_projection table.
                           Uses market-implied inflation from TES breakeven.
                           If None, falls back to flat inflation_annual.
            inflation_annual: Annual inflation for flat fallback projection (decimal).
                             Only used when uvr_projection is not provided.

        Returns:
            List of dicts with UVR and COP amounts per period
        """
        if isinstance(start_date, datetime):
            start_date = datetime_to_ql(start_date)
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        if periodicity not in PERIODICITY_MONTHS:
            raise ValueError(f"Invalid periodicity '{periodicity}'.")
        if days_count not in DAY_COUNT_MAP:
            raise ValueError(f"Invalid days_count '{days_count}'.")
        if amortization_type not in AMORTIZATION_TYPES:
            raise ValueError(f"Invalid amortization_type '{amortization_type}'.")
        if grace_type not in GRACE_TYPES:
            raise ValueError(f"Invalid grace_type '{grace_type}'.")

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

        uvr_hist_df, last_known_uvr, last_known_date = self._prepare_uvr_data(db_info)
        uvr_proj_df, _, _ = self._prepare_uvr_data(uvr_projection)

        eval_date = ql.Settings.instance().evaluationDate
        ibr_ref = self.cm.ibr_handle.currentLink().referenceDate()

        # French annuity in UVR
        if amortization_type == "french":
            period_rate = self._compute_interest_factor(
                rate_pct, dates[0], dates[1], days_count, periodicity,
            )
            if abs(period_rate) < 1e-10:
                annuity_uvr = notional_uvr / capital_periods
            else:
                annuity_uvr = notional_uvr * period_rate / (
                    1 - (1 + period_rate) ** (-capital_periods)
                )

        rows = []
        balance_uvr = notional_uvr
        accumulated_interest_uvr = 0.0

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

            # Interest in UVR
            if i < grace_period_interest:
                interest_uvr = 0.0
                accumulated_interest_uvr += balance_uvr * interest_factor
            else:
                if accumulated_interest_uvr > 0 and i == grace_period_interest:
                    balance_uvr += accumulated_interest_uvr
                    accumulated_interest_uvr = 0.0
                interest_uvr = balance_uvr * interest_factor

            # Principal in UVR
            if i < grace_period_principal:
                principal_uvr = 0.0
            else:
                if amortization_type == "linear":
                    principal_uvr = notional_uvr / capital_periods
                    if i == n_periods - 1:
                        principal_uvr = balance_uvr
                elif amortization_type == "bullet":
                    principal_uvr = balance_uvr if i == n_periods - 1 else 0.0
                elif amortization_type == "french":
                    principal_uvr = annuity_uvr - interest_uvr
                    if i == n_periods - 1:
                        principal_uvr = balance_uvr

            payment_uvr = interest_uvr + principal_uvr
            ending_balance_uvr = balance_uvr - principal_uvr

            # UVR → COP conversion
            uvr_value = self._get_uvr_value(
                p_end, uvr_hist_df, uvr_proj_df,
                inflation_annual, last_known_uvr, last_known_date,
            )

            interest_cop = interest_uvr * uvr_value
            principal_cop = principal_uvr * uvr_value
            payment_cop = payment_uvr * uvr_value
            balance_cop = balance_uvr * uvr_value
            ending_balance_cop = ending_balance_uvr * uvr_value

            # Discount factor (COP)
            if p_end > ibr_ref:
                df = self.cm.ibr_handle.discount(p_end)
            else:
                df = 1.0

            pv_cop = payment_cop * df

            rows.append({
                "period": i + 1,
                "date_start": ql_to_datetime(p_start).strftime("%Y-%m-%d"),
                "date_end": ql_to_datetime(p_end).strftime("%Y-%m-%d"),
                # UVR amounts
                "beginning_balance_uvr": round(balance_uvr, 4),
                "interest_uvr": round(interest_uvr, 4),
                "principal_uvr": round(principal_uvr, 4),
                "payment_uvr": round(payment_uvr, 4),
                "ending_balance_uvr": round(ending_balance_uvr, 4),
                # COP amounts
                "uvr_value": round(uvr_value, 4),
                "beginning_balance_cop": round(balance_cop, 2),
                "interest_cop": round(interest_cop, 2),
                "principal_cop": round(principal_cop, 2),
                "payment_cop": round(payment_cop, 2),
                "ending_balance_cop": round(ending_balance_cop, 2),
                # Pricing
                "rate_pct": rate_pct,
                "discount_factor": round(df, 8),
                "pv_cop": round(pv_cop, 2),
                "status": status,
            })

            balance_uvr = ending_balance_uvr

        return rows

    def price(
        self,
        notional_uvr: float,
        start_date,
        maturity_date,
        rate_pct: float,
        periodicity: str = "Mensual",
        days_count: str = "por_dias_360",
        amortization_type: str = "french",
        grace_type: str = None,
        grace_period: int = 0,
        db_info: dict = None,
        uvr_projection: dict = None,
        inflation_annual: float = 0.05,
    ) -> dict:
        """
        Price a UVR-indexed loan and return analytics.

        Returns:
            dict with: npv_cop, notional_uvr, rate_pct, principal_outstanding_uvr,
                       principal_outstanding_cop, accrued_interest_cop, duration,
                       tenor_years, periods_total, periods_remaining
        """
        cfs = self.cashflows(
            notional_uvr=notional_uvr,
            start_date=start_date,
            maturity_date=maturity_date,
            rate_pct=rate_pct,
            periodicity=periodicity,
            days_count=days_count,
            amortization_type=amortization_type,
            grace_type=grace_type,
            grace_period=grace_period,
            db_info=db_info,
            uvr_projection=uvr_projection,
            inflation_annual=inflation_annual,
        )

        future_cfs = [cf for cf in cfs if cf["status"] != "settled"]
        npv_cop = sum(cf["pv_cop"] for cf in future_cfs)

        principal_outstanding_uvr = future_cfs[0]["beginning_balance_uvr"] if future_cfs else 0.0
        principal_outstanding_cop = future_cfs[0]["beginning_balance_cop"] if future_cfs else 0.0

        # Accrued interest
        accrued_interest_cop = 0.0
        eval_date = ql.Settings.instance().evaluationDate
        for cf in cfs:
            if cf["status"] == "current":
                p_start = datetime_to_ql(datetime.strptime(cf["date_start"], "%Y-%m-%d"))
                p_end = datetime_to_ql(datetime.strptime(cf["date_end"], "%Y-%m-%d"))
                dc = ql.Actual365Fixed()
                total_days = dc.dayCount(p_start, p_end)
                elapsed_days = dc.dayCount(p_start, eval_date)
                if total_days > 0:
                    accrued_interest_cop = cf["interest_cop"] * elapsed_days / total_days
                break

        # Duration
        total_pv = sum(cf["pv_cop"] for cf in future_cfs) if future_cfs else 0.0
        eval_dt = ql_to_datetime(eval_date)
        duration = 0.0
        if total_pv > 0:
            for cf in future_cfs:
                cf_date = datetime.strptime(cf["date_end"], "%Y-%m-%d")
                t_years = (cf_date - eval_dt).days / 365.25
                duration += t_years * cf["pv_cop"] / total_pv

        # Tenor
        if cfs:
            last_date = datetime.strptime(cfs[-1]["date_end"], "%Y-%m-%d")
            tenor_years = (last_date - eval_dt).days / 365.25
        else:
            tenor_years = 0.0

        return {
            "npv_cop": round(npv_cop, 2),
            "notional_uvr": notional_uvr,
            "rate_pct": rate_pct,
            "inflation_annual": inflation_annual,
            "principal_outstanding_uvr": round(principal_outstanding_uvr, 4),
            "principal_outstanding_cop": round(principal_outstanding_cop, 2),
            "accrued_interest_cop": round(accrued_interest_cop, 2),
            "total_value_cop": round(principal_outstanding_cop + accrued_interest_cop, 2),
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
        notional_uvr: float,
        start_date,
        maturity_date,
        rate_pct: float,
        periodicity: str = "Mensual",
        days_count: str = "por_dias_360",
        amortization_type: str = "french",
        grace_type: str = None,
        grace_period: int = 0,
        db_info: dict = None,
        uvr_projection: dict = None,
        inflation_annual: float = 0.05,
        bump_bps: float = 1.0,
    ) -> dict:
        """DV01: sensitivity of NPV to a 1bp parallel shift in IBR discount curve."""
        common_args = dict(
            notional_uvr=notional_uvr,
            start_date=start_date,
            maturity_date=maturity_date,
            rate_pct=rate_pct,
            periodicity=periodicity,
            days_count=days_count,
            amortization_type=amortization_type,
            grace_type=grace_type,
            grace_period=grace_period,
            db_info=db_info,
            uvr_projection=uvr_projection,
            inflation_annual=inflation_annual,
        )

        base = self.price(**common_args)
        base_npv = base["npv_cop"]

        self.cm.bump_ibr(bump_bps)
        bumped = self.price(**common_args)
        bumped_npv = bumped["npv_cop"]
        self.cm.bump_ibr(-bump_bps)

        return {
            "dv01_cop": round(bumped_npv - base_npv, 2),
            "bump_bps": bump_bps,
            "base_npv": base_npv,
            "bumped_npv": bumped_npv,
        }

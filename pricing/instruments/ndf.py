"""
USD/COP Non-Deliverable Forward (NDF) pricer.

An NDF settles in USD: at maturity, the difference between the contracted
forward rate and the fixing rate (BanRep TRM) is exchanged in USD.

Pricing uses the NDF-implied COP discount curve (from market forward points),
NOT the IBR curve. The NDF market has its own basis (credit, convertibility,
supply/demand) that differs from interest rate parity.

Forward FX rate:
  F(T) = Spot * DF_USD(T) / DF_COP_ndf(T)

NPV_COP = Notional_USD * (Forward - Strike) * DF_COP_ndf(T_delivery)

The NDF curve is bootstrapped from cop_fwd_points market data via FxSwapRateHelper.
"""
import QuantLib as ql
import pandas as pd
from datetime import datetime
from utilities.date_functions import datetime_to_ql, ql_to_datetime
from utilities.colombia_calendar import calendar_colombia


class NdfPricer:
    """
    Prices USD/COP Non-Deliverable Forwards.
    Requires CurveManager with IBR and SOFR curves built, plus FX spot.
    """

    def __init__(self, curve_manager):
        self.cm = curve_manager
        self.calendar_cop = calendar_colombia()
        self.calendar_usd = ql.UnitedStates(ql.UnitedStates.FederalReserve)
        self.joint_calendar = ql.JointCalendar(self.calendar_cop, self.calendar_usd)

    def implied_forward(self, maturity_date: ql.Date, spot: float = None) -> float:
        """
        Calculate the forward FX rate from the NDF-implied COP curve.
        F(T) = Spot * DF_USD(T) / DF_COP_ndf(T)

        Falls back to IBR/SOFR parity if NDF curve is not built.

        Args:
            maturity_date: QL date for the forward
            spot: USD/COP spot rate. If None, uses cm.fx_spot.

        Returns:
            Forward USD/COP rate
        """
        spot = spot or self.cm.fx_spot
        if spot is None:
            raise ValueError("FX spot rate not set. Call cm.set_fx_spot() first.")

        df_usd = self.cm.sofr_handle.discount(maturity_date)

        # Use NDF curve if available, otherwise fall back to IBR
        if self.cm.ndf_curve is not None:
            df_cop = self.cm.ndf_handle.discount(maturity_date)
        else:
            df_cop = self.cm.ibr_handle.discount(maturity_date)

        return spot * df_usd / df_cop

    def forward_points(self, maturity_date: ql.Date, spot: float = None) -> float:
        """Calculate forward points (Forward - Spot) from interest rate parity."""
        fwd = self.implied_forward(maturity_date, spot)
        spot = spot or self.cm.fx_spot
        return fwd - spot

    def price(
        self,
        notional_usd: float,
        strike: float,
        maturity_date,
        direction: str = "buy",
        spot: float = None,
    ) -> dict:
        """
        Price an NDF position using implied forward from curves.

        Args:
            notional_usd: Notional amount in USD
            strike: Contracted forward rate (USD/COP)
            maturity_date: Maturity/fixing date (datetime or ql.Date)
            direction: 'buy' (long USD) or 'sell' (short USD)
            spot: Current spot rate (overrides cm.fx_spot)

        Returns:
            dict with full pricing details
        """
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        spot = spot or self.cm.fx_spot
        sign = 1.0 if direction == "buy" else -1.0

        forward = self.implied_forward(maturity_date, spot)
        df_usd = self.cm.sofr_handle.discount(maturity_date)

        # Use NDF curve for COP discounting if available
        if self.cm.ndf_curve is not None:
            df_cop = self.cm.ndf_handle.discount(maturity_date)
        else:
            df_cop = self.cm.ibr_handle.discount(maturity_date)

        npv_cop = sign * notional_usd * (forward - strike) * df_cop
        npv_usd = npv_cop / spot
        delta_cop = sign * notional_usd * df_cop

        # Carry (theta): daily P&L from forward points decay
        day_counter = ql.Actual360()
        ref_date = self.cm.sofr_handle.referenceDate()
        days_to_maturity = day_counter.dayCount(ref_date, maturity_date)
        carry_cop_daily = npv_cop / max(days_to_maturity, 1)
        carry_usd_daily = npv_usd / max(days_to_maturity, 1)

        return {
            "npv_usd": npv_usd,
            "npv_cop": npv_cop,
            "forward": forward,
            "forward_points": forward - spot,
            "strike": strike,
            "df_usd": df_usd,
            "df_cop": df_cop,
            "delta_cop": delta_cop,
            "carry_cop_daily": round(carry_cop_daily, 2),
            "carry_usd_daily": round(carry_usd_daily, 2),
            "days_to_maturity": days_to_maturity,
            "notional_usd": notional_usd,
            "direction": direction,
            "spot": spot,
            "maturity": ql_to_datetime(maturity_date),
            "curve_source": "ndf" if self.cm.ndf_curve is not None else "ibr_sofr_parity",
        }

    def price_from_market_points(
        self,
        notional_usd: float,
        strike: float,
        maturity_date,
        market_forward: float,
        direction: str = "buy",
        spot: float = None,
    ) -> dict:
        """
        Price an NDF using market-observed forward rate (from cop_fwd_points)
        instead of implied forward from interest rate parity.

        Args:
            market_forward: Market-observed forward rate (mid from cop_fwd_points)
        """
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        spot = spot or self.cm.fx_spot
        sign = 1.0 if direction == "buy" else -1.0
        df_usd = self.cm.sofr_handle.discount(maturity_date)

        if self.cm.ndf_curve is not None:
            df_cop = self.cm.ndf_handle.discount(maturity_date)
        else:
            df_cop = self.cm.ibr_handle.discount(maturity_date)

        npv_cop = sign * notional_usd * (market_forward - strike) * df_cop
        npv_usd = npv_cop / spot

        return {
            "npv_usd": npv_usd,
            "npv_cop": npv_cop,
            "forward": market_forward,
            "forward_points": market_forward - spot,
            "strike": strike,
            "df_usd": df_usd,
            "df_cop": df_cop,
            "notional_usd": notional_usd,
            "direction": direction,
            "spot": spot,
            "maturity": ql_to_datetime(maturity_date),
        }

    def implied_curve(
        self, cop_fwd_df: pd.DataFrame, spot: float = None
    ) -> pd.DataFrame:
        """
        Build a forward curve comparing market NDF vs IBR/SOFR parity.

        Shows the NDF basis: how much the market forward deviates from
        the theoretical interest rate parity forward (IBR/SOFR).

        Args:
            cop_fwd_df: DataFrame from cop_fwd_points table
                        (columns: tenor, tenor_months, mid, fwd_points)
            spot: USD/COP spot rate

        Returns:
            DataFrame with: tenor, tenor_months, forward_market,
                           forward_irt_parity, basis
        """
        spot = spot or self.cm.fx_spot
        results = []

        for _, row in cop_fwd_df.iterrows():
            months = int(row["tenor_months"])
            if months == 0:
                continue
            mat = self.cm.valuation_date + ql.Period(months, ql.Months)
            fwd_market = float(row["mid"])

            # IBR/SOFR interest rate parity forward (theoretical)
            df_usd = self.cm.sofr_handle.discount(mat)
            df_cop_ibr = self.cm.ibr_handle.discount(mat)
            fwd_irt = spot * df_usd / df_cop_ibr

            results.append({
                "tenor": row["tenor"],
                "tenor_months": months,
                "forward_market": fwd_market,
                "forward_irt_parity": fwd_irt,
                "basis": fwd_market - fwd_irt,
            })

        return pd.DataFrame(results)

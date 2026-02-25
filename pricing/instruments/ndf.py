"""
USD/COP Non-Deliverable Forward (NDF) pricer.

An NDF settles in USD: at maturity, the difference between the contracted
forward rate and the fixing rate (BanRep TRM) is exchanged in USD.

The implied forward FX rate from interest rate parity is:
  F(T) = Spot * DF_COP(T) / DF_USD(T)

NPV = Notional_USD * (Forward - Strike) * DF_USD(T_delivery)

Supports both:
  - Implied forwards from IBR/SOFR curves (interest rate parity)
  - Market-observed forwards from FXEmpire cop_fwd_points table
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
        Calculate the implied forward FX rate from interest rate parity.
        F(T) = Spot * DF_COP(T) / DF_USD(T)

        Args:
            maturity_date: QL date for the forward
            spot: USD/COP spot rate. If None, uses cm.fx_spot.

        Returns:
            Implied forward USD/COP rate
        """
        spot = spot or self.cm.fx_spot
        if spot is None:
            raise ValueError("FX spot rate not set. Call cm.set_fx_spot() first.")

        df_cop = self.cm.ibr_handle.discount(maturity_date)
        df_usd = self.cm.sofr_handle.discount(maturity_date)

        return spot * df_cop / df_usd

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
        df_cop = self.cm.ibr_handle.discount(maturity_date)

        npv_cop = sign * notional_usd * (forward - strike) * df_usd
        npv_usd = npv_cop / spot
        delta_cop = sign * notional_usd * df_cop

        return {
            "npv_usd": npv_usd,
            "npv_cop": npv_cop,
            "forward": forward,
            "forward_points": forward - spot,
            "strike": strike,
            "df_usd": df_usd,
            "df_cop": df_cop,
            "delta_cop": delta_cop,
            "notional_usd": notional_usd,
            "direction": direction,
            "spot": spot,
            "maturity": ql_to_datetime(maturity_date),
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

        npv_cop = sign * notional_usd * (market_forward - strike) * df_usd
        npv_usd = npv_cop / spot

        return {
            "npv_usd": npv_usd,
            "npv_cop": npv_cop,
            "forward": market_forward,
            "forward_points": market_forward - spot,
            "strike": strike,
            "df_usd": df_usd,
            "notional_usd": notional_usd,
            "direction": direction,
            "spot": spot,
            "maturity": ql_to_datetime(maturity_date),
        }

    def implied_curve(
        self, cop_fwd_df: pd.DataFrame, spot: float = None
    ) -> pd.DataFrame:
        """
        Build an implied forward curve comparing market vs model.

        Args:
            cop_fwd_df: DataFrame from cop_fwd_points table
                        (columns: tenor, tenor_months, mid, fwd_points)
            spot: USD/COP spot rate

        Returns:
            DataFrame with: tenor, tenor_months, forward_market, forward_implied, basis
        """
        spot = spot or self.cm.fx_spot
        results = []

        for _, row in cop_fwd_df.iterrows():
            months = int(row["tenor_months"])
            if months == 0:
                continue
            mat = self.cm.valuation_date + ql.Period(months, ql.Months)
            fwd_implied = self.implied_forward(mat, spot)
            fwd_market = row["mid"]

            results.append({
                "tenor": row["tenor"],
                "tenor_months": months,
                "forward_market": fwd_market,
                "forward_implied": fwd_implied,
                "basis": fwd_market - fwd_implied,
            })

        return pd.DataFrame(results)

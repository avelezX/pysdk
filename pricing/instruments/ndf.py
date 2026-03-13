"""
USD/COP Non-Deliverable Forward (NDF) pricer.

An NDF settles in USD: at maturity, the difference between the contracted
forward rate and the fixing rate (BanRep TRM) is exchanged in USD.

The implied forward FX rate from interest rate parity is:
  F(T) = Spot * DF_USD(T) / DF_COP(T)

NPV_COP = Notional_USD * (Forward - Strike) * DF_COP(T_delivery)

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

    @property
    def _cop_handle(self):
        """
        COP discount handle for NDF pricing.

        Returns cm.ndf_handle when the NDF market curve is built (preferred —
        captures convertibility risk and market basis over interest rate parity).
        Falls back to cm.ibr_handle when the NDF curve is not available.
        """
        if self.cm.ndf_curve is not None:
            return self.cm.ndf_handle
        return self.cm.ibr_handle

    def implied_forward(self, maturity_date: ql.Date, spot: float = None) -> float:
        """
        Calculate the implied forward FX rate from interest rate parity.
        F(T) = Spot * DF_USD(T) / DF_COP(T)

        When cm.ndf_curve is available, DF_COP comes from the NDF market curve
        (bootstrapped from cop_fwd_points / market_marks.ndf), capturing the
        market basis. Otherwise falls back to the IBR curve.

        Args:
            maturity_date: QL date for the forward
            spot: USD/COP spot rate. If None, uses cm.fx_spot.

        Returns:
            Implied forward USD/COP rate
        """
        spot = spot or self.cm.fx_spot
        if spot is None:
            raise ValueError("FX spot rate not set. Call cm.set_fx_spot() first.")

        df_cop = self._cop_handle.discount(maturity_date)
        df_usd = self.cm.sofr_handle.discount(maturity_date)

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
        Price an NDF position using the implied forward from interest rate parity.

        The implied forward is: F(T) = Spot * DF_USD(T) / DF_COP(T)
        NPV is discounted to today using the COP discount factor:
            NPV_COP = sign * notional_usd * (F - strike) * DF_COP(T)

        Args:
            notional_usd (float): Notional in USD. Must be positive.
            strike (float): Contracted forward rate (USD/COP). This is the
                rate agreed at inception; was the at-market forward at trade time.
            maturity_date (datetime | ql.Date): Fixing/settlement date of the NDF.
            direction (str): 'buy' = long USD (receive USD, pay COP if spot rises).
                'sell' = short USD (pay USD, receive COP if spot falls).
            spot (float | None): USD/COP spot rate. Defaults to cm.fx_spot.

        Returns:
            dict with keys:
                npv_usd (float): Net present value in USD.
                npv_cop (float): Net present value in COP.
                forward (float): Implied forward rate USD/COP at maturity.
                forward_points (float): Forward minus spot.
                strike (float): Contracted forward rate.
                df_usd (float): SOFR discount factor at maturity.
                df_cop (float): IBR discount factor at maturity.
                delta_cop (float): FX delta in COP (sensitivity to a 1-unit spot move).
                    = sign * notional_usd * df_cop
                notional_usd (float): USD notional.
                direction (str): 'buy' or 'sell'.
                spot (float): USD/COP spot rate used.
                maturity (datetime): Maturity date as Python datetime.
        """
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        spot = spot or self.cm.fx_spot
        sign = 1.0 if direction == "buy" else -1.0

        forward = self.implied_forward(maturity_date, spot)
        df_usd = self.cm.sofr_handle.discount(maturity_date)
        df_cop = self._cop_handle.discount(maturity_date)

        npv_cop = sign * notional_usd * (forward - strike) * df_cop
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
        Price an NDF using a market-observed forward rate instead of the
        implied forward from interest rate parity.

        Use this when you have a reliable market quote (e.g., from cop_fwd_points
        table) and want to avoid model dependency on IBR/SOFR curve calibration.

        NPV is still discounted using the COP discount factor (NDF market curve if
        available, else IBR fallback):
            NPV_COP = sign * notional_usd * (market_forward - strike) * DF_COP(T)

        Args:
            notional_usd (float): Notional in USD. Must be positive.
            strike (float): Contracted forward rate (USD/COP).
            maturity_date (datetime | ql.Date): Fixing/settlement date of the NDF.
            market_forward (float): Market-observed forward rate (mid from
                cop_fwd_points table, or dealer quote).
            direction (str): 'buy' = long USD. 'sell' = short USD.
            spot (float | None): USD/COP spot rate. Defaults to cm.fx_spot.

        Returns:
            dict with keys:
                npv_usd (float): Net present value in USD.
                npv_cop (float): Net present value in COP.
                forward (float): Market forward rate used for pricing.
                forward_points (float): market_forward minus spot.
                strike (float): Contracted forward rate.
                df_usd (float): SOFR discount factor at maturity.
                df_cop (float): COP discount factor at maturity (NDF market curve
                    if available, else IBR).
                delta_cop (float): FX delta in COP (sensitivity to a 1-unit spot move).
                    = sign * notional_usd * df_cop
                notional_usd (float): USD notional.
                direction (str): 'buy' or 'sell'.
                spot (float): USD/COP spot rate used.
                maturity (datetime): Maturity date as Python datetime.
        """
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        spot = spot or self.cm.fx_spot
        sign = 1.0 if direction == "buy" else -1.0
        df_usd = self.cm.sofr_handle.discount(maturity_date)
        df_cop = self._cop_handle.discount(maturity_date)

        npv_cop = sign * notional_usd * (market_forward - strike) * df_cop
        npv_usd = npv_cop / spot
        delta_cop = sign * notional_usd * df_cop

        return {
            "npv_usd": npv_usd,
            "npv_cop": npv_cop,
            "forward": market_forward,
            "forward_points": market_forward - spot,
            "strike": strike,
            "df_usd": df_usd,
            "df_cop": df_cop,
            "delta_cop": delta_cop,
            "notional_usd": notional_usd,
            "direction": direction,
            "spot": spot,
            "maturity": ql_to_datetime(maturity_date),
        }

    def pnl_inception(
        self,
        notional_usd: float,
        strike: float,
        maturity_date,
        direction: str = "buy",
        spot: float = None,
        fx_inception: float = None,
    ) -> dict:
        """
        P&L from inception decomposed into FX and rate components.

        At trade inception the NDF was at-market (NPV=0). The current NPV
        can be attributed to two orthogonal risk factors:

          FX component:  reprice with current spot but inception-implied
                         discount factors (i.e., only spot moved).
          Rate component: reprice with inception spot but current discount
                          factors (i.e., only curves moved).
          Cross-gamma:   residual interaction term.

        The inception forward is reconstructed from the strike (which was
        the at-market forward at trade time).

        Args:
            notional_usd: USD notional
            strike: Contracted forward rate (was at-market at inception)
            maturity_date: Maturity date
            direction: 'buy' or 'sell'
            spot: Current spot (defaults to cm.fx_spot)
            fx_inception: Spot FX at trade inception. If None, derived from
                          strike and current curves as approximation.

        Returns:
            dict with npv_total, pnl_fx, pnl_rates, pnl_cross, forward_current
        """
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        spot_current = spot or self.cm.fx_spot
        sign = 1.0 if direction == "buy" else -1.0

        # Current market values
        df_cop = self._cop_handle.discount(maturity_date)
        df_usd = self.cm.sofr_handle.discount(maturity_date)
        forward_current = spot_current * df_usd / df_cop

        npv_total = sign * notional_usd * (forward_current - strike) * df_cop

        # Inception FX: if not provided, approximate from strike
        # At inception: strike = fx_inception * df_usd_inception / df_cop_inception
        # We don't have inception curves, so use fx_inception if provided,
        # otherwise approximate: fx_inception ~ strike * df_cop / df_usd
        # (assumes curves haven't moved much — acceptable for decomposition)
        if fx_inception is None:
            fx_inception = strike * df_cop / df_usd

        # FX-only scenario: spot moves to current, curves stay at inception
        # At inception the forward was at-market so F_inception = strike
        # If only spot moved: F_fx_only = spot_current * (strike / fx_inception)
        # because the ratio df_usd/df_cop is unchanged
        fwd_fx_only = spot_current * (strike / fx_inception)
        npv_fx_only = sign * notional_usd * (fwd_fx_only - strike) * df_cop

        # Rate-only scenario: curves move to current, spot stays at inception
        fwd_rate_only = fx_inception * df_usd / df_cop
        npv_rate_only = sign * notional_usd * (fwd_rate_only - strike) * df_cop

        # Cross-gamma residual
        pnl_cross = npv_total - npv_fx_only - npv_rate_only

        return {
            "npv_cop": npv_total,
            "npv_usd": npv_total / spot_current,
            "pnl_fx_cop": npv_fx_only,
            "pnl_rates_cop": npv_rate_only,
            "pnl_cross_cop": pnl_cross,
            "forward_current": forward_current,
            "forward_fx_only": fwd_fx_only,
            "forward_rate_only": fwd_rate_only,
            "strike": strike,
            "spot_current": spot_current,
            "fx_inception": fx_inception,
            "df_cop": df_cop,
            "df_usd": df_usd,
            "direction": direction,
            "notional_usd": notional_usd,
            "maturity": ql_to_datetime(maturity_date),
        }

    def dv01(
        self,
        notional_usd: float,
        strike: float,
        maturity_date,
        direction: str = "buy",
        spot: float = None,
        bump_bps: float = 1.0,
    ) -> dict:
        """
        Compute DV01 (rate sensitivity) for an NDF position.

        Bumps IBR and SOFR curves independently by bump_bps and measures
        the NPV change. Returns DV01 per curve and total.

        Args:
            notional_usd: USD notional
            strike: Contracted forward rate
            maturity_date: Maturity date
            direction: 'buy' or 'sell'
            spot: Current spot
            bump_bps: Bump size in basis points (default 1bp)

        Returns:
            dict with dv01_ibr, dv01_sofr, dv01_total (all in COP)
        """
        if isinstance(maturity_date, datetime):
            maturity_date = datetime_to_ql(maturity_date)

        base = self.price(notional_usd, strike, maturity_date, direction, spot)
        base_npv = base["npv_cop"]

        # IBR bump
        self.cm.bump_ibr(bump_bps)
        ibr_bumped = self.price(notional_usd, strike, maturity_date, direction, spot)
        dv01_ibr = ibr_bumped["npv_cop"] - base_npv
        self.cm.bump_ibr(-bump_bps)

        # SOFR bump
        self.cm.bump_sofr(bump_bps)
        sofr_bumped = self.price(notional_usd, strike, maturity_date, direction, spot)
        dv01_sofr = sofr_bumped["npv_cop"] - base_npv
        self.cm.bump_sofr(-bump_bps)

        return {
            "dv01_ibr_cop": dv01_ibr,
            "dv01_sofr_cop": dv01_sofr,
            "dv01_total_cop": dv01_ibr + dv01_sofr,
            "bump_bps": bump_bps,
            "base_npv_cop": base_npv,
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

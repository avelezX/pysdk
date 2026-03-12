"""
CurveManager: Central orchestrator for all yield curves.

Holds RelinkableYieldTermStructureHandle for each curve so that instruments
reference the handle, not the curve directly. When curves are rebuilt or
individual nodes are bumped, all instruments automatically reprice.

Key pattern: Each curve's market data nodes are ql.SimpleQuote objects.
Modifying a SimpleQuote value triggers an automatic curve recalculation,
which propagates through the RelinkableHandle to all attached instruments.

Usage:
    from pricing.curves.curve_manager import CurveManager
    from pricing.data.market_data import MarketDataLoader

    loader = MarketDataLoader()
    cm = CurveManager()

    # Build curves from latest Supabase data
    cm.build_ibr_curve(loader.fetch_ibr_quotes())
    cm.build_sofr_curve(loader.fetch_sofr_curve())
    cm.set_fx_spot(loader.fetch_usdcop_spot())

    # Modify a single node (instruments auto-update)
    cm.set_ibr_node('ibr_5y', 9.75)

    # Parallel shift entire curve
    cm.bump_ibr(10)  # +10 bps

    # Reset to market values
    cm.reset_to_market()
"""
import QuantLib as ql
import pandas as pd
from datetime import datetime
from utilities.date_functions import datetime_to_ql

from pricing.curves.ibr_curve import build_ibr_curve, IBR_DETAILS
from pricing.curves.sofr_curve import build_sofr_curve, sofr_quantlib_det
from pricing.curves.tes_curve import build_tes_curve
from pricing.curves.ndf_curve import build_ndf_curve


class CurveManager:
    """
    Manages all yield curves and their RelinkableYieldTermStructureHandles.

    Attributes:
        ibr_handle / sofr_handle / tes_handle: RelinkableYieldTermStructureHandle
        ibr_quotes / sofr_quotes: dict of {key: SimpleQuote} for node overrides
        ibr_index / sofr_index: OvernightIndex linked to handles (for projection)
        fx_spot: USD/COP spot rate
    """

    def __init__(self, valuation_date: ql.Date = None):
        self.valuation_date = valuation_date or ql.Date.todaysDate()
        ql.Settings.instance().evaluationDate = self.valuation_date

        # Relinkable handles (empty initially)
        self.ibr_handle = ql.RelinkableYieldTermStructureHandle()
        self.sofr_handle = ql.RelinkableYieldTermStructureHandle()
        self.tes_handle = ql.RelinkableYieldTermStructureHandle()
        self.ndf_handle = ql.RelinkableYieldTermStructureHandle()

        # Underlying curves
        self.ibr_curve = None
        self.sofr_curve = None
        self.tes_curve = None
        self.ndf_curve = None

        # SimpleQuote dictionaries for node overrides
        self.ibr_quotes = {}    # {tenor_key: SimpleQuote}
        self.sofr_quotes = {}   # {tenor_months: SimpleQuote}

        # Original market values for reset
        self._ibr_market = {}   # {tenor_key: original_value}
        self._sofr_market = {}  # {tenor_months: original_value}

        # Overnight indices linked to forwarding curves
        self.ibr_index = ql.OvernightIndex(
            "IBR1D", 1, ql.COPCurrency(),
            IBR_DETAILS["calendar"],
            ql.Actual360(),
            self.ibr_handle,
        )

        self.sofr_index = ql.OvernightIndex(
            "SOFR", 0, ql.USDCurrency(),
            sofr_quantlib_det["calendar"],
            ql.Actual360(),
            self.sofr_handle,
        )

        # FX data
        self.fx_spot = None

        # Build timestamps
        self._ibr_built_at = None
        self._sofr_built_at = None
        self._tes_built_at = None
        self._ndf_built_at = None

    # ── Valuation Date ──

    def set_valuation_date(self, dt):
        """Update global valuation date. Accepts ql.Date or datetime."""
        if isinstance(dt, datetime):
            dt = datetime_to_ql(dt)
        self.valuation_date = dt
        ql.Settings.instance().evaluationDate = dt

    # ── FX ──

    def set_fx_spot(self, usdcop: float):
        """Set the USD/COP spot rate."""
        self.fx_spot = usdcop

    # ── Curve Builders ──

    def build_ibr_curve(self, db_info: dict) -> ql.YieldTermStructure:
        """
        Build (or rebuild) the IBR curve and link it to the handle.

        Args:
            db_info: Dict with keys ibr_1d, ibr_1m, ..., ibr_20y.
                     Values are lists where [0] is rate in percent.
        """
        self.ibr_curve, self.ibr_quotes = build_ibr_curve(
            db_info, self.valuation_date
        )
        self.ibr_handle.linkTo(self.ibr_curve)
        self._ibr_market = {k: sq.value() for k, sq in self.ibr_quotes.items()}
        self._ibr_built_at = datetime.now()
        return self.ibr_curve

    def build_sofr_curve(self, df: pd.DataFrame) -> ql.YieldTermStructure:
        """
        Build (or rebuild) the SOFR curve and link it to the handle.

        Args:
            df: DataFrame with columns: tenor_months, swap_rate (in percent)
        """
        self.sofr_curve, self.sofr_quotes = build_sofr_curve(
            df, self.valuation_date
        )
        self.sofr_handle.linkTo(self.sofr_curve)
        self._sofr_market = {k: sq.value() for k, sq in self.sofr_quotes.items()}
        self._sofr_built_at = datetime.now()
        return self.sofr_curve

    def build_tes_curve(
        self,
        bond_info_df: pd.DataFrame,
        market_prices_df: pd.DataFrame,
        currency: str = "COP",
        excluded_bonds: list = None,
    ) -> ql.YieldTermStructure:
        """
        Build (or rebuild) the TES curve and link it to the handle.
        """
        self.tes_curve = build_tes_curve(
            bond_info_df, market_prices_df,
            self.valuation_date, currency, excluded_bonds,
        )
        self.tes_handle.linkTo(self.tes_curve)
        self._tes_built_at = datetime.now()
        return self.tes_curve

    def build_ndf_from_marks(self, ndf_marks: dict, spot: float) -> ql.YieldTermStructure:
        """
        Build NDF-implied COP discount curve from market_marks.ndf snapshot.

        Converts the pre-computed marks dict to a DataFrame and calls build_ndf_curve().
        The resulting curve captures the NDF market basis (convertibility risk, supply/demand)
        that the IBR curve misses. Use this for NDF pricing; IBR remains for IBR swaps.

        Args:
            ndf_marks: dict from market_marks.ndf JSONB.
                       Keys = tenor_months as str, values = {fwd_pts_cop, F_market, deval_ea}.
                       e.g. {"1": {"fwd_pts_cop": 27.25, "F_market": 3830.25, ...}}
            spot: USD/COP spot rate (from market_marks.fx_spot or cm.fx_spot)

        Returns:
            NDF-implied COP DiscountCurve (also linked to ndf_handle).
        """
        rows = [
            {"tenor_months": int(k), "mid": v["F_market"]}
            for k, v in ndf_marks.items()
        ]
        df = pd.DataFrame(rows).sort_values("tenor_months")
        self.ndf_curve, _ = build_ndf_curve(df, spot, self.sofr_handle, self.valuation_date)
        self.ndf_handle.linkTo(self.ndf_curve)
        self._ndf_built_at = datetime.now()
        return self.ndf_curve

    def build_all(self, loader, target_date: str = None) -> dict:
        """
        Build all curves from a MarketDataLoader instance.

        NDF curve priority:
          1. market_marks.ndf (pre-computed, preferred)
          2. cop_fwd_points raw (bootstrap on the fly, fallback)
          3. None — NdfPricer falls back to ibr_handle

        Args:
            loader: MarketDataLoader instance
            target_date: ISO date string for historical builds. None = latest.

        Returns:
            dict with build status per curve
        """
        results = {}

        ibr_data = loader.fetch_ibr_quotes(target_date=target_date)
        if ibr_data:
            self.build_ibr_curve(ibr_data)
            results["ibr"] = "built"

        sofr_data = loader.fetch_sofr_curve(target_date=target_date)
        if not sofr_data.empty:
            self.build_sofr_curve(sofr_data)
            results["sofr"] = "built"

        fx = loader.fetch_usdcop_spot(target_date=target_date)
        if fx:
            self.set_fx_spot(fx)
            results["fx_spot"] = fx

        # ── NDF curve: market_marks first, raw fallback ──
        if self.fx_spot and self.sofr_curve is not None:
            marks = loader.fetch_marks(target_date=target_date)
            if marks and marks.get("ndf"):
                self.build_ndf_from_marks(marks["ndf"], self.fx_spot)
                results["ndf"] = "built_from_marks"
            else:
                cop_fwd = loader.fetch_cop_forwards(target_date=target_date)
                if not cop_fwd.empty:
                    self.ndf_curve, _ = build_ndf_curve(
                        cop_fwd, self.fx_spot, self.sofr_handle, self.valuation_date
                    )
                    self.ndf_handle.linkTo(self.ndf_curve)
                    self._ndf_built_at = datetime.now()
                    results["ndf"] = "built_from_raw"

        return results

    # ── Node Overrides (What-If Scenarios) ──

    def set_ibr_node(self, tenor_key: str, new_rate_pct: float):
        """
        Modify a single IBR curve node. The curve auto-recalculates.

        Args:
            tenor_key: e.g., 'ibr_5y', 'ibr_1m'
            new_rate_pct: New rate in percent (e.g., 9.75 for 9.75%)
        """
        if tenor_key not in self.ibr_quotes:
            raise KeyError(
                f"Unknown IBR tenor '{tenor_key}'. "
                f"Available: {list(self.ibr_quotes.keys())}"
            )
        self.ibr_quotes[tenor_key].setValue(new_rate_pct / 100.0)

    def set_sofr_node(self, tenor_months: int, new_rate_pct: float):
        """
        Modify a single SOFR curve node. The curve auto-recalculates.

        Args:
            tenor_months: e.g., 60 for 5Y
            new_rate_pct: New rate in percent (e.g., 4.25 for 4.25%)
        """
        if tenor_months not in self.sofr_quotes:
            raise KeyError(
                f"Unknown SOFR tenor '{tenor_months}M'. "
                f"Available: {list(self.sofr_quotes.keys())}"
            )
        self.sofr_quotes[tenor_months].setValue(new_rate_pct / 100.0)

    def bump_ibr(self, bps: float):
        """Parallel shift the entire IBR curve by bps basis points."""
        shift = bps / 10000.0
        for sq in self.ibr_quotes.values():
            sq.setValue(sq.value() + shift)

    def bump_sofr(self, bps: float):
        """Parallel shift the entire SOFR curve by bps basis points."""
        shift = bps / 10000.0
        for sq in self.sofr_quotes.values():
            sq.setValue(sq.value() + shift)

    def reset_to_market(self):
        """Reset all SimpleQuotes to their original market values."""
        for key, original in self._ibr_market.items():
            if key in self.ibr_quotes:
                self.ibr_quotes[key].setValue(original)
        for key, original in self._sofr_market.items():
            if key in self.sofr_quotes:
                self.sofr_quotes[key].setValue(original)

    # ── Convenience Methods ──

    def ibr_discount(self, dt: ql.Date) -> float:
        return self.ibr_handle.discount(dt)

    def sofr_discount(self, dt: ql.Date) -> float:
        return self.sofr_handle.discount(dt)

    def ibr_zero_rate(self, dt: ql.Date, compounding: int = ql.Continuous) -> float:
        return self.ibr_handle.zeroRate(dt, ql.Actual360(), compounding).rate()

    def sofr_zero_rate(self, dt: ql.Date, compounding: int = ql.Continuous) -> float:
        return self.sofr_handle.zeroRate(dt, ql.Actual360(), compounding).rate()

    def ibr_forward_rate(self, start: ql.Date, end: ql.Date) -> float:
        return self.ibr_handle.forwardRate(start, end, ql.Actual360(), ql.Simple).rate()

    def sofr_forward_rate(self, start: ql.Date, end: ql.Date) -> float:
        return self.sofr_handle.forwardRate(start, end, ql.Actual360(), ql.Simple).rate()

    # ── Status ──

    def status(self) -> dict:
        """Return build status of all curves."""
        def _curve_info(curve, built_at, quotes):
            if curve is None:
                return {"built": False}
            info = {
                "built": True,
                "timestamp": str(built_at),
                "nodes": {str(k): round(sq.value() * 100, 4) for k, sq in quotes.items()},
            }
            return info

        return {
            "valuation_date": str(self.valuation_date),
            "fx_spot": self.fx_spot,
            "ibr": _curve_info(self.ibr_curve, self._ibr_built_at, self.ibr_quotes),
            "sofr": _curve_info(self.sofr_curve, self._sofr_built_at, self.sofr_quotes),
            "tes": {
                "built": self.tes_curve is not None,
                "timestamp": str(self._tes_built_at),
            },
            "ndf": {
                "built": self.ndf_curve is not None,
                "timestamp": str(self._ndf_built_at),
            },
        }

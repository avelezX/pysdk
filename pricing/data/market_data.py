"""
Market data loader for Supabase tables.
Centralizes all market data queries using the same REST API pattern as the runners.
"""
import os
import requests
import pandas as pd
from datetime import date


SUPABASE_URL = os.getenv(
    "XTY_URL", "https://tvpehjbqxpiswkqszwwv.supabase.co"
)
SUPABASE_KEY = os.getenv(
    "XTY_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2cGVoamJxeHBpc3drcXN6d3d2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE2OTY0NTEzODksImV4cCI6MjAxMjAyNzM4OX0.LZW0i9HU81lCdyjAdqjwwF4hkuSVtsJsSDQh7blzozw",
)
COLLECTOR_BEARER = os.getenv(
    "COLLECTOR_BEARER",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiAiY29sbGVjdG9yIiwiZXhwIjogMTg0NzI4ODUyMCwiaWF0IjogMTczNjk1NTc1MiwiaXNzIjogImh0dHBzOi8vdHZwZWhqYnF4cGlzd2txc3p3d3Yuc3VwYWJhc2UuY28iLCJlbWFpbCI6ICJzdmVsZXpzYWZmb25AZ21haWwuY29tIiwicm9sZSI6ICJjb2xsZWN0b3IifQ.5HX_n8SsXN4xPslndvyyYubdlDLFg2_uAUIwinEi-eU",
)


class MarketDataLoader:
    """
    Fetches latest market data from Supabase REST API.
    Uses the xerenity schema profile, same as collectors.
    """

    def __init__(self, supabase_url: str = None, supabase_key: str = None,
                 bearer_token: str = None):
        self.url = supabase_url or SUPABASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "apikey": supabase_key or SUPABASE_KEY,
            "Authorization": f"Bearer {bearer_token or COLLECTOR_BEARER}",
            "Content-Type": "application/json",
            "Accept-Profile": "xerenity",
            "Content-Profile": "xerenity",
        })

    # ── Generic helpers ──

    def _get(self, table: str, params: str = "") -> list:
        resp = self.session.get(f"{self.url}/rest/v1/{table}?{params}")
        resp.raise_for_status()
        return resp.json()

    def _latest_date(self, table: str, date_col: str = "fecha") -> str | None:
        data = self._get(table, f"select={date_col}&order={date_col}.desc&limit=1")
        if data:
            return data[0][date_col]
        return None

    # ── SOFR Swap Curve ──

    def fetch_sofr_curve(self, target_date: str = None) -> pd.DataFrame:
        """
        Fetch SOFR par swap rates from sofr_swap_curve table.
        Returns DataFrame with columns: tenor_months, swap_rate
        """
        if target_date is None:
            target_date = self._latest_date("sofr_swap_curve")
        if target_date is None:
            return pd.DataFrame(columns=["tenor_months", "swap_rate"])

        data = self._get(
            "sofr_swap_curve",
            f"select=tenor_months,swap_rate&fecha=eq.{target_date}&order=tenor_months.asc",
        )
        return pd.DataFrame(data)

    # ── IBR Quotes ──

    # BanRep deposit series IDs for IBR tenors
    _BANREP_DEPOSITS = {
        "ibr_1d": 9,
        "ibr_1m": 11,
        "ibr_3m": 13,
        "ibr_6m": 15,
        "ibr_12m": 17,
    }

    # Swap rate tables accessible to collector role
    _SWAP_TABLES = {
        "ibr_2y": "ibr_2y",
        "ibr_5y": "ibr_5y",
        "ibr_10y": "ibr_10y",
    }

    def fetch_ibr_quotes(self, target_date: str = None) -> dict:
        """
        Fetch IBR curve quotes from source tables + materialized view fallback.

        Deposits (1D-12M): from banrep_series_value_v2 (BanRep official rates).
        Swaps (2Y-10Y): from individual ibr_Xy tables (direct, always fresh).
        Swaps (15Y, 20Y): from ibr_quotes_curve materialized view (restricted
                          tables not accessible to collector role directly).

        Returns dict: {ibr_1d: [rate], ibr_1m: [rate], ...} rates in percent.
        """
        result = {}

        # Deposits from BanRep
        for key, serie_id in self._BANREP_DEPOSITS.items():
            if target_date is None:
                data = self._get(
                    "banrep_series_value_v2",
                    f"select=valor&id_serie=eq.{serie_id}&order=fecha.desc&limit=1",
                )
            else:
                data = self._get(
                    "banrep_series_value_v2",
                    f"select=valor&id_serie=eq.{serie_id}&fecha=eq.{target_date}&limit=1",
                )
            if data and data[0].get("valor") is not None:
                result[key] = [data[0]["valor"]]

        # Swaps 2Y-10Y from accessible tables
        for key, table in self._SWAP_TABLES.items():
            if target_date is None:
                data = self._get(
                    table,
                    "select=close&order=day.desc&limit=1",
                )
            else:
                data = self._get(
                    table,
                    f"select=close&day=eq.{target_date}&limit=1",
                )
            if data and data[0].get("close") is not None:
                result[key] = [data[0]["close"]]

        # 15Y and 20Y from materialized view (tables not accessible directly)
        try:
            mv_data = self._get(
                "ibr_quotes_curve",
                "select=ibr_15y,ibr_20y&order=fecha.desc&limit=1",
            )
            if mv_data:
                row = mv_data[0]
                if row.get("ibr_15y") is not None:
                    result["ibr_15y"] = [row["ibr_15y"]]
                if row.get("ibr_20y") is not None:
                    result["ibr_20y"] = [row["ibr_20y"]]
        except Exception:
            pass  # Curve builds without 15Y/20Y if view unavailable

        return result

    # ── COP Forward Points ──

    def fetch_cop_forwards(self, target_date: str = None) -> pd.DataFrame:
        """
        Fetch COP forward points from cop_fwd_points table.
        Returns DataFrame with columns: tenor, tenor_months, bid, ask, mid, fwd_points
        """
        if target_date is None:
            target_date = self._latest_date("cop_fwd_points")
        if target_date is None:
            return pd.DataFrame()

        data = self._get(
            "cop_fwd_points",
            f"select=tenor,tenor_months,bid,ask,mid,fwd_points&fecha=eq.{target_date}&order=tenor_months.asc",
        )
        return pd.DataFrame(data)

    # ── TES Bond Info ──

    def fetch_tes_bond_info(self) -> pd.DataFrame:
        """
        Fetch TES bond master data from the tes table.
        Returns DataFrame with columns: name, emision, maduracion, cupon, moneda
        """
        data = self._get("tes", "select=name,emision,maduracion,cupon,moneda")
        df = pd.DataFrame(data)
        if not df.empty:
            df["emision"] = pd.to_datetime(df["emision"])
            df["maduracion"] = pd.to_datetime(df["maduracion"])
        return df

    # ── USD/COP Spot Rate ──

    def fetch_usdcop_spot(self, target_date: str = None) -> float | None:
        """
        Fetch latest USD/COP spot rate from cop_fwd_points (SN tenor mid).
        """
        if target_date is None:
            target_date = self._latest_date("cop_fwd_points")
        if target_date is None:
            return None

        data = self._get(
            "cop_fwd_points",
            f"select=mid&fecha=eq.{target_date}&tenor=eq.SN&limit=1",
        )
        if data and "mid" in data[0]:
            return float(data[0]["mid"])
        return None

    # ── US Reference Rates ──

    def fetch_sofr_spot(self, target_date: str = None) -> float | None:
        """
        Fetch latest SOFR overnight rate from us_reference_rates table.
        Returns rate as decimal (e.g., 0.0430 for 4.30%).
        """
        if target_date is None:
            data = self._get(
                "us_reference_rates",
                "select=rate&rate_type=eq.SOFR&order=fecha.desc&limit=1",
            )
        else:
            data = self._get(
                "us_reference_rates",
                f"select=rate&rate_type=eq.SOFR&fecha=eq.{target_date}&limit=1",
            )
        if data and "rate" in data[0]:
            return float(data[0]["rate"]) / 100.0
        return None

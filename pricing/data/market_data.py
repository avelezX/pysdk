"""
Market data loader for Supabase tables.
Centralizes all market data queries using the same REST API pattern as the runners.
"""
import os
import requests
import pandas as pd
from datetime import date


SUPABASE_URL = os.getenv("XTY_URL")
SUPABASE_KEY = os.getenv("XTY_TOKEN")
COLLECTOR_BEARER = os.getenv("COLLECTOR_BEARER")


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
        Fetch IBR curve quotes from source tables.

        Deposits (1D-12M): from banrep_series_value_v2 (BanRep official rates).
        Swaps (2Y-10Y): from individual ibr_Xy tables (direct, always fresh).

        Returns dict: {ibr_1d: [rate], ibr_1m: [rate], ...} rates in percent.
        """
        result = {}
        today = date.today().isoformat()

        # Deposits from BanRep (filter out future dates)
        for key, serie_id in self._BANREP_DEPOSITS.items():
            if target_date is None:
                data = self._get(
                    "banrep_series_value_v2",
                    f"select=valor&id_serie=eq.{serie_id}"
                    f"&fecha=lte.{today}&order=fecha.desc&limit=1",
                )
            else:
                data = self._get(
                    "banrep_series_value_v2",
                    f"select=valor&id_serie=eq.{serie_id}&fecha=eq.{target_date}&limit=1",
                )
            if data and data[0].get("valor") is not None:
                result[key] = [data[0]["valor"]]

        # Swaps 2Y-10Y from accessible tables (filter out future dates)
        for key, table in self._SWAP_TABLES.items():
            if target_date is None:
                data = self._get(
                    table,
                    f"select=close&day=lte.{today}&order=day.desc&limit=1",
                )
            else:
                data = self._get(
                    table,
                    f"select=close&day=eq.{target_date}&limit=1",
                )
            if data and data[0].get("close") is not None:
                result[key] = [data[0]["close"]]

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

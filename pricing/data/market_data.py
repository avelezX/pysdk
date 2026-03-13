"""
Market data loader for Supabase tables.
Centralizes all market data queries using the same REST API pattern as the runners.
"""
from __future__ import annotations

import os
import requests
import pandas as pd
from datetime import date, timedelta
from typing import Optional


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
        # apikey: XTY_TOKEN (anon publishable key — identifies the project to Supabase)
        # bearer: COLLECTOR_BEARER (collector role JWT — has SELECT on all xerenity
        #         market data tables via grants + RLS policies).
        key = supabase_key or SUPABASE_KEY
        bearer = bearer_token or COLLECTOR_BEARER or key
        self.session = requests.Session()
        self.session.headers.update({
            "apikey": key,
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
            "Accept-Profile": "xerenity",
            "Content-Profile": "xerenity",
        })

    # ── Generic helpers ──

    def _get(self, table: str, params: str = "") -> list:
        resp = self.session.get(f"{self.url}/rest/v1/{table}?{params}")
        resp.raise_for_status()
        return resp.json()

    def _latest_date(self, table: str, date_col: str = "fecha") -> Optional[str]:
        data = self._get(table, f"select={date_col}&order={date_col}.desc&limit=1")
        if data:
            return data[0][date_col]
        return None

    # ── SOFR Swap Curve ──

    def fetch_sofr_curve(self, target_date: str = None) -> pd.DataFrame:
        """
        Fetch SOFR par swap rates from sofr_swap_curve table.
        Returns DataFrame with columns: tenor_months, swap_rate

        Uses lte (not eq) so that historical and intraday requests still find
        the most recent available curve when today's data hasn't been collected
        yet (SOFR collector runs at 21:00 UTC).
        """
        effective_date = target_date or date.today().isoformat()

        # Get the most recent fecha <= effective_date
        latest = self._get(
            "sofr_swap_curve",
            f"select=fecha&fecha=lte.{effective_date}&order=fecha.desc&limit=1",
        )
        if not latest:
            return pd.DataFrame(columns=["tenor_months", "swap_rate"])

        actual_date = latest[0]["fecha"]
        data = self._get(
            "sofr_swap_curve",
            f"select=tenor_months,swap_rate&fecha=eq.{actual_date}&order=tenor_months.asc",
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

        # Deposits from BanRep — use lte for both live and historical to handle
        # series that aren't published every day (e.g. ibr_12m).
        effective_date = target_date or today
        for key, serie_id in self._BANREP_DEPOSITS.items():
            data = self._get(
                "banrep_series_value_v2",
                f"select=valor&id_serie=eq.{serie_id}"
                f"&fecha=lte.{effective_date}&order=fecha.desc&limit=1",
            )
            if data and data[0].get("valor") is not None:
                result[key] = [data[0]["valor"]]

        # Swaps 2Y-10Y from accessible tables — same lte approach.
        for key, table in self._SWAP_TABLES.items():
            data = self._get(
                table,
                f"select=close&day=lte.{effective_date}&order=day.desc&limit=1",
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

    def fetch_usdcop_spot(self, target_date: str = None) -> Optional[float]:
        """
        Fetch latest USD/COP spot rate.

        Primary source: currency_hour table (SET-ICAP intraday prices).
          - Live: last trade of the day.
          - Historical (target_date provided): last trade of that date.

        Fallback: cop_fwd_points SN tenor mid (FXEmpire), used when
        currency_hour has no data for the requested date (e.g. weekends,
        dates before the SET-ICAP collector was live).
        """
        value = self._fetch_usdcop_setfx(target_date)
        if value is not None:
            return value
        return self._fetch_usdcop_fwd_points_sn(target_date)

    def _fetch_usdcop_setfx(self, target_date: str = None) -> Optional[float]:
        """Fetch USD/COP from currency_hour (SET-ICAP). Returns None if no data."""
        if target_date is None:
            data = self._get(
                "currency_hour",
                "select=value&currency=eq.USD:COP&order=time.desc&limit=1",
            )
        else:
            next_date = (date.fromisoformat(target_date) + timedelta(days=1)).isoformat()
            data = self._get(
                "currency_hour",
                f"select=value&currency=eq.USD:COP"
                f"&time=gte.{target_date}T00:00:00&time=lt.{next_date}T00:00:00"
                f"&order=time.desc&limit=1",
            )
        if data and "value" in data[0]:
            return float(data[0]["value"])
        return None

    def _fetch_usdcop_fwd_points_sn(self, target_date: str = None) -> Optional[float]:
        """Fallback: fetch USD/COP from cop_fwd_points SN tenor mid (FXEmpire)."""
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

    # ── BanRep TRM (serie 25) ──

    def fetch_trm(self, fecha: str) -> Optional[float]:
        """
        Fetch TRM (Tasa Representativa del Mercado) for a given date.

        Source: banrep_series_value_v2, serie_id=25.
        Uses lte to handle weekends/holidays — returns the last published TRM
        on or before the requested date.

        Args:
            fecha: ISO date string, e.g. '2026-03-12'

        Returns:
            TRM as float (COP per 1 USD), or None if not found.
        """
        data = self._get(
            "banrep_series_value_v2",
            f"select=valor,fecha&id_serie=eq.25"
            f"&fecha=lte.{fecha}&order=fecha.desc&limit=1",
        )
        if data and data[0].get("valor") is not None:
            return float(data[0]["valor"])
        return None

    # ── Store Marks Snapshot ──

    def store_marks(self, fecha: str, fx_spot: float, sofr_on: float,
                    ibr: dict, sofr: dict, ndf: dict) -> bool:
        """
        Upsert a daily market marks snapshot into the market_marks table.

        Args:
            fecha:   ISO date string, e.g. '2026-03-03'
            fx_spot: USD/COP spot rate (SET-ICAP)
            sofr_on: SOFR overnight rate in %
            ibr:     dict of IBR nodes, e.g. {'ibr_1d': 9.636, ...}
            sofr:    dict of SOFR zero rates by tenor_months, e.g. {'1': 3.661, ...}
            ndf:     dict of NDF forwards by tenor_months,
                     e.g. {'1': {'fwd_pts_cop': 27.25, 'F_market': 3830.25, 'deval_ea': 8.95}}

        Returns:
            True if stored successfully.
        """
        import json
        payload = {
            "fecha":    fecha,
            "fx_spot":  fx_spot,
            "sofr_on":  sofr_on,
            "ibr":      ibr,
            "sofr":     sofr,
            "ndf":      ndf,
        }
        resp = self.session.post(
            f"{self.url}/rest/v1/market_marks",
            headers={
                "Prefer": "resolution=merge-duplicates",   # upsert on fecha PK
            },
            json=payload,
        )
        resp.raise_for_status()
        return True

    def fetch_marks(self, target_date: str = None) -> dict | None:
        """
        Fetch daily market marks snapshot from market_marks table.

        Args:
            target_date: ISO date string. None = latest available.

        Returns:
            dict with keys: fecha, fx_spot, sofr_on, ibr, sofr, ndf
            None if no data found.
        """
        if target_date is None:
            target_date = self._latest_date("market_marks")
        if target_date is None:
            return None
        data = self._get(
            "market_marks",
            f"select=fecha,fx_spot,sofr_on,ibr,sofr,ndf&fecha=eq.{target_date}&limit=1",
        )
        return data[0] if data else None

    # ── US Reference Rates ──

    def fetch_sofr_spot(self, target_date: str = None) -> Optional[float]:
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

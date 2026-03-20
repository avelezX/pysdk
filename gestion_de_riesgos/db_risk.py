"""
Capa de acceso a datos de Supabase para el modulo de gestion de riesgos.

Uses the same REST API pattern as pricing/data/market_data.py:
  - XTY_URL + XTY_TOKEN + COLLECTOR_BEARER (already configured in Fly.io)
  - No user login required

Tablas esperadas en Supabase (schema xerenity):
- risk_prices:        Precios historicos de futuros (MAIZ, AZUCAR, CACAO, USD)
- risk_positions:     Posiciones del benchmark y portafolio GR
- risk_portfolio_config: Configuracion del portafolio (fechas, parametros)
"""

import os
import requests
import pandas as pd

SUPABASE_URL = os.getenv("XTY_URL")
SUPABASE_KEY = os.getenv("XTY_TOKEN")
COLLECTOR_BEARER = os.getenv("COLLECTOR_BEARER")


def _session() -> requests.Session:
    """Create a Supabase REST session with collector credentials."""
    key = SUPABASE_KEY
    bearer = COLLECTOR_BEARER or key
    s = requests.Session()
    s.headers.update({
        "apikey": key,
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
        "Accept-Profile": "xerenity",
        "Content-Profile": "xerenity",
    })
    return s


def _get(table: str, params: str = "") -> list:
    resp = _session().get(f"{SUPABASE_URL}/rest/v1/{table}?{params}")
    resp.raise_for_status()
    return resp.json()


def _post(table: str, payload: list[dict], extra_headers: dict = None) -> None:
    s = _session()
    if extra_headers:
        s.headers.update(extra_headers)
    resp = s.post(f"{SUPABASE_URL}/rest/v1/{table}", json=payload)
    resp.raise_for_status()


# ── Risk Prices ──

def _fetch_risk_prices_raw(initial_date: str, final_date: str) -> pd.DataFrame:
    """Fetch raw risk_prices rows (date, asset, price, contract)."""
    data = _get(
        "risk_prices",
        f"select=date,asset,price,contract"
        f"&date=gte.{initial_date}&date=lte.{final_date}"
        f"&order=date.asc",
    )
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)


def get_risk_prices(initial_date: str, final_date: str) -> pd.DataFrame:
    """
    Obtiene precios historicos de activos de riesgo.

    Args:
        initial_date: Fecha inicio (YYYY-MM-DD)
        final_date: Fecha fin (YYYY-MM-DD)

    Returns:
        DataFrame con columnas: ['date', 'MAIZ', 'AZUCAR', 'CACAO', 'USD']
    """
    df = _fetch_risk_prices_raw(initial_date, final_date)
    if df.empty:
        return df

    # Pivotar: filas (date, asset, price) -> columnas ['date', 'MAIZ', 'AZUCAR', ...]
    if 'asset' in df.columns and 'price' in df.columns:
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        pivot = df.pivot_table(index='date', columns='asset', values='price', aggfunc='last')
        pivot = pivot.reset_index().sort_values('date').reset_index(drop=True)
        return pivot

    return df


def get_risk_contracts(initial_date: str, final_date: str) -> dict:
    """
    Retorna el ultimo contrato (ticker) usado por cada activo en el rango.

    Returns:
        dict: {'MAIZ': 'ZCH26', 'AZUCAR': 'SBK6', 'CACAO': 'CCH26', 'USD': 'TRM'}
    """
    df = _fetch_risk_prices_raw(initial_date, final_date)
    if df.empty:
        return {}

    contracts = {}
    for asset in df['asset'].unique():
        asset_df = df[df['asset'] == asset].sort_values('date')
        last_contract = asset_df['contract'].dropna().iloc[-1] if asset_df['contract'].notna().any() else None
        if last_contract:
            contracts[asset] = last_contract
    return contracts


# ── Risk Positions ──

def get_risk_positions(portfolio_id: str = None) -> list[dict]:
    """
    Obtiene las posiciones actuales (benchmark y GR).

    Returns:
        Lista de dicts con: asset, position, position_type ('benchmark' o 'gr'), weight
    """
    params = "select=*&order=asset.asc"
    if portfolio_id:
        params += f"&portfolio_id=eq.{portfolio_id}"
    data = _get("risk_positions", params)
    return data or []


# ── Portfolio Config ──

def get_portfolio_config(portfolio_id: str = None) -> dict:
    """
    Obtiene la configuracion del portafolio de riesgos.

    Returns:
        dict con: price_date_start, price_date_end, rolling_window, confidence_level
    """
    params = "select=*&limit=1"
    if portfolio_id:
        params += f"&id=eq.{portfolio_id}"
    data = _get("risk_portfolio_config", params)
    return data[0] if data else {}


# ── Upserts ──

def upsert_risk_prices(records: list[dict]) -> None:
    """
    Inserta o actualiza precios historicos en la tabla risk_prices.

    Args:
        records: Lista de dicts con: date, asset, price
    """
    _post("risk_prices", records, {"Prefer": "resolution=merge-duplicates"})


def upsert_risk_positions(records: list[dict]) -> None:
    """
    Inserta o actualiza posiciones en la tabla risk_positions.

    Args:
        records: Lista de dicts con: asset, position, position_type, weight, portfolio_id
    """
    _post("risk_positions", records, {"Prefer": "resolution=merge-duplicates"})


# ── Latest Prices ──

def get_latest_prices() -> dict:
    """
    Obtiene el ultimo precio disponible de cada activo.

    Returns:
        dict: {'MAIZ': 435.75, 'AZUCAR': 13.84, ...}
    """
    data = _get("risk_prices", "select=*&order=date.desc&limit=1")
    if not data:
        return {}
    row = data[0]
    return {k: v for k, v in row.items() if k != 'date' and k != 'id'}

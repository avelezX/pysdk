"""
Capa de acceso a datos de Supabase para el modulo de gestion de riesgos.

Uses the same REST API pattern as pricing/data/market_data.py:
  - XTY_URL + XTY_TOKEN + COLLECTOR_BEARER (already configured in Fly.io)
  - No user login required

Tablas esperadas en Supabase (schema xerenity):
- risk_prices:              Precios historicos de futuros (MAIZ, AZUCAR, CACAO, USD)
- risk_positions:           Posiciones del benchmark y portafolio GR
- risk_portfolio_config:    Configuracion del portafolio (fechas, parametros)
- risk_futures_portfolio:   Posiciones individuales de futuros (portafolio GR)
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


def _patch(table: str, filters: str, payload: dict) -> None:
    s = _session()
    resp = s.patch(f"{SUPABASE_URL}/rest/v1/{table}?{filters}", json=payload)
    resp.raise_for_status()


def _delete(table: str, filters: str) -> None:
    s = _session()
    resp = s.delete(f"{SUPABASE_URL}/rest/v1/{table}?{filters}")
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


# ── Futures Portfolio (posiciones individuales GR) ──

def get_futures_portfolio(portfolio_id: str = None, active_only: bool = True) -> list[dict]:
    """
    Obtiene las posiciones individuales de futuros.

    Args:
        portfolio_id: Filtrar por portafolio especifico
        active_only: Solo posiciones activas (default True)

    Returns:
        Lista de dicts con: id, asset, contract, direction, nominal,
        entry_price, entry_date, active, closed_date, closed_price, rolled_to
    """
    params = "select=*&order=entry_date.desc"
    if active_only:
        params += "&active=eq.true"
    if portfolio_id:
        params += f"&portfolio_id=eq.{portfolio_id}"
    return _get("risk_futures_portfolio", params) or []


def get_futures_position(position_id: str) -> dict:
    """Obtiene una posicion individual por su ID."""
    data = _get("risk_futures_portfolio", f"select=*&id=eq.{position_id}")
    return data[0] if data else {}


def upsert_futures_positions(records: list[dict]) -> None:
    """Inserta o actualiza posiciones de futuros."""
    _post("risk_futures_portfolio", records, {"Prefer": "resolution=merge-duplicates"})


def close_futures_position(
    position_id: str,
    closed_date: str,
    closed_price: float,
    rolled_to: str = None,
) -> None:
    """
    Cierra una posicion de futuros (o la marca como rolada).

    Args:
        position_id: UUID de la posicion
        closed_date: Fecha de cierre (YYYY-MM-DD)
        closed_price: Precio de cierre/roll
        rolled_to: Codigo del nuevo contrato si es roll (ej: 'ZCN26')
    """
    payload = {
        "active": False,
        "closed_date": closed_date,
        "closed_price": closed_price,
    }
    if rolled_to:
        payload["rolled_to"] = rolled_to
    _patch("risk_futures_portfolio", f"id=eq.{position_id}", payload)


def delete_futures_position(position_id: str) -> None:
    """Elimina una posicion de futuros por su ID."""
    _delete("risk_futures_portfolio", f"id=eq.{position_id}")

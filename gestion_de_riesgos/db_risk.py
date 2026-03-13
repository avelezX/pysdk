"""
Capa de acceso a datos de Supabase para el modulo de gestion de riesgos.

Tablas esperadas en Supabase (schema xerenity):
- risk_prices:        Precios historicos de futuros (MAIZ, AZUCAR, CACAO, USD)
- risk_positions:     Posiciones del benchmark y portafolio GR
- risk_portfolio_config: Configuracion del portafolio (fechas, parametros)
"""

import pandas as pd


def _get_xty():
    """Lazy import para evitar fallo al importar si Supabase no esta configurado."""
    from db_call.db_call import xty
    return xty


def get_risk_prices(initial_date: str, final_date: str) -> pd.DataFrame:
    """
    Obtiene precios historicos de activos de riesgo.

    Args:
        initial_date: Fecha inicio (YYYY-MM-DD)
        final_date: Fecha fin (YYYY-MM-DD)

    Returns:
        DataFrame con columnas: ['date', 'MAIZ', 'AZUCAR', 'CACAO', 'USD']
    """
    xty = _get_xty()
    data = xty.session.table('risk_prices') \
        .select('*') \
        .gte('date', initial_date) \
        .lte('date', final_date) \
        .order('date', desc=False) \
        .execute().data

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # Pivotar: filas (date, asset, price) -> columnas ['date', 'MAIZ', 'AZUCAR', ...]
    if 'asset' in df.columns and 'price' in df.columns:
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        pivot = df.pivot_table(index='date', columns='asset', values='price', aggfunc='last')
        pivot = pivot.reset_index().sort_values('date').reset_index(drop=True)
        return pivot

    return df


def get_risk_positions(portfolio_id: str = None) -> list[dict]:
    """
    Obtiene las posiciones actuales (benchmark y GR).

    Returns:
        Lista de dicts con: asset, position, position_type ('benchmark' o 'gr'), weight
    """
    xty = _get_xty()
    query = xty.session.table('risk_positions').select('*')
    if portfolio_id:
        query = query.eq('portfolio_id', portfolio_id)

    data = query.order('asset', desc=False).execute().data
    return data or []


def get_portfolio_config(portfolio_id: str = None) -> dict:
    """
    Obtiene la configuracion del portafolio de riesgos.

    Returns:
        dict con: price_date_start, price_date_end, rolling_window, confidence_level
    """
    xty = _get_xty()
    query = xty.session.table('risk_portfolio_config').select('*')
    if portfolio_id:
        query = query.eq('id', portfolio_id)

    data = query.limit(1).execute().data
    return data[0] if data else {}


def upsert_risk_prices(records: list[dict]) -> None:
    """
    Inserta o actualiza precios historicos en la tabla risk_prices.

    Args:
        records: Lista de dicts con: date, asset, price
    """
    xty = _get_xty()
    xty.session.table('risk_prices').upsert(records).execute()


def upsert_risk_positions(records: list[dict]) -> None:
    """
    Inserta o actualiza posiciones en la tabla risk_positions.

    Args:
        records: Lista de dicts con: asset, position, position_type, weight, portfolio_id
    """
    xty = _get_xty()
    xty.session.table('risk_positions').upsert(records).execute()


def get_latest_prices() -> dict:
    """
    Obtiene el ultimo precio disponible de cada activo.

    Returns:
        dict: {'MAIZ': 435.75, 'AZUCAR': 13.84, ...}
    """
    xty = _get_xty()
    data = xty.session.table('risk_prices') \
        .select('*') \
        .order('date', desc=True) \
        .limit(1) \
        .execute().data

    if not data:
        return {}

    row = data[0]
    return {k: v for k, v in row.items() if k != 'date' and k != 'id'}

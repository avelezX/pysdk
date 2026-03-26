"""
Portafolio de futuros para gestion de riesgos.

Calcula P&L mensual y desde inicio para posiciones individuales
de futuros de commodities (MAIZ, AZUCAR, CACAO) operadas en cuentas de margen.

Logica de precios:
- Precio Compra: siempre el entry_price (fijo)
- Precio Actual: ultimo precio disponible en Supabase
- Precio Previo: si la posicion se abrio en el mes seleccionado -> entry_price
                 si ya lleva mas de 1 mes -> ultimo dia habil del mes anterior

P&L Mes = (Precio Actual - Precio Previo) x nominal x multiplicador x direccion
P&L Inicio = (Precio Actual - Precio Compra) x nominal x multiplicador x direccion

Soporta posiciones LONG y SHORT, y roll de contratos.
"""

from datetime import datetime, date, timedelta
import pandas as pd
import math


# Multiplicador por contrato (unidades fisicas por 1 contrato)
CONTRACT_MULTIPLIERS = {
    'MAIZ':   5_000,     # bushels por contrato (ZC, CBOT)
    'AZUCAR': 112_000,   # libras por contrato (SB, ICE)
    'CACAO':  10,         # toneladas metricas por contrato (CC, ICE)
}

DIRECTION_SIGN = {'LONG': 1, 'SHORT': -1}

PRICE_UNITS = {
    'MAIZ': 'cents/bu',
    'AZUCAR': 'cents/lb',
    'CACAO': 'USD/ton',
}


def _safe_round(value, decimals=2):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(value, decimals)


def _last_business_day_of_prev_month(ref_date: date) -> date:
    """
    Ultimo dia habil del mes anterior a ref_date.
    Misma logica que benchmark_factors() en risk_management_server.
    """
    first_of_current = ref_date.replace(day=1)
    last_cal_day = first_of_current - timedelta(days=1)
    wd = last_cal_day.weekday()  # 0=Mon ... 5=Sat, 6=Sun
    if wd == 5:
        return last_cal_day - timedelta(days=1)
    elif wd == 6:
        return last_cal_day - timedelta(days=2)
    return last_cal_day


def _find_price(prices_df: pd.DataFrame, asset: str, target_date: date):
    """
    Busca el precio mas reciente en o antes de target_date.
    Returns (price, actual_date_str) o (None, None).
    """
    if asset not in prices_df.columns:
        return None, None

    target_str = target_date.strftime('%Y-%m-%d')
    mask = prices_df['date'] <= target_str
    subset = prices_df.loc[mask, ['date', asset]].dropna(subset=[asset])
    if subset.empty:
        return None, None

    row = subset.iloc[-1]
    return float(row[asset]), str(row['date'])[:10]


class FuturesPortfolioCalculator:
    """
    Calcula P&L para un portafolio de posiciones individuales de futuros.

    Cada posicion tiene:
    - asset, contract, direction (LONG/SHORT), nominal (# contratos)
    - entry_price, entry_date

    Calcula:
    - valor_t:       nominal * multiplier * precio actual
    - precio_previo: entry_price si la posicion se abrio en el mes seleccionado,
                     ultimo dia habil del mes anterior si la posicion es mas vieja
    - pnl_inception: P&L desde precio de compra
    - pnl_month:     P&L del mes (desde precio_previo)
    """

    def __init__(
        self,
        positions: list[dict],
        prices_history: pd.DataFrame,
        filter_date: str,
    ):
        self.positions = positions
        self.prices = prices_history
        self.filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date()

    def calculate(self) -> list[dict]:
        ref = self.filter_date
        month_start = _last_business_day_of_prev_month(ref)

        rows = []
        totals = {
            'valor_t': 0, 'valor_t1': 0, 'pnl_inception': 0, 'pnl_month': 0,
        }

        for pos in self.positions:
            asset = pos['asset']
            direction = pos['direction']
            nominal = pos['nominal']
            entry_price = float(pos['entry_price'])
            multiplier = CONTRACT_MULTIPLIERS.get(asset, 1)
            dir_sign = DIRECTION_SIGN.get(direction, 1)

            # Precio actual: ultimo disponible hasta filter_date
            current_price, current_date = _find_price(self.prices, asset, ref)

            # Precio previo: depende de cuando se abrio la posicion
            entry_dt = datetime.strptime(pos['entry_date'], '%Y-%m-%d').date()
            if entry_dt > month_start:
                # Posicion abierta en el mes corriente -> previo = precio de compra
                precio_previo = entry_price
                precio_previo_date = pos['entry_date']
            else:
                # Posicion de meses anteriores -> previo = ultimo dia habil mes anterior
                precio_previo, precio_previo_date = _find_price(
                    self.prices, asset, month_start
                )

            # Calculos
            valor_t = None
            valor_t1 = None
            pnl_inception = None
            pnl_month = None

            if current_price is not None:
                valor_t = nominal * multiplier * current_price
                pnl_inception = (current_price - entry_price) * nominal * multiplier * dir_sign

            if precio_previo is not None:
                valor_t1 = nominal * multiplier * precio_previo

            if current_price is not None and precio_previo is not None:
                pnl_month = (current_price - precio_previo) * nominal * multiplier * dir_sign

            row = {
                'id': pos.get('id'),
                'asset': asset,
                'contract': pos['contract'],
                'direction': direction,
                'nominal': nominal,
                'multiplier': multiplier,
                'entry_price': entry_price,
                'entry_date': pos['entry_date'],
                'current_price': _safe_round(current_price, 4),
                'current_price_date': current_date,
                'precio_previo': _safe_round(precio_previo, 4),
                'precio_previo_date': precio_previo_date,
                'valor_t': _safe_round(valor_t),
                'valor_t1': _safe_round(valor_t1),
                'pnl_inception': _safe_round(pnl_inception),
                'pnl_month': _safe_round(pnl_month),
                'price_unit': PRICE_UNITS.get(asset, ''),
            }
            rows.append(row)

            # Acumular totales
            for key in totals:
                val = row[key]
                if val is not None:
                    totals[key] += val

        # Fila total
        rows.append({
            'id': None,
            'asset': 'Total',
            'contract': None,
            'direction': None,
            'nominal': None,
            'multiplier': None,
            'entry_price': None,
            'entry_date': None,
            'current_price': None,
            'current_price_date': None,
            'precio_previo': None,
            'precio_previo_date': None,
            'valor_t': _safe_round(totals['valor_t']),
            'valor_t1': _safe_round(totals['valor_t1']),
            'pnl_inception': _safe_round(totals['pnl_inception']),
            'pnl_month': _safe_round(totals['pnl_month']),
            'price_unit': None,
        })

        return rows

    @staticmethod
    def execute_roll(
        position: dict,
        new_contract: str,
        roll_price: float,
        roll_date: str,
        new_entry_price: float = None,
    ) -> tuple[dict, dict]:
        """
        Prepara los datos para un roll de contrato.

        Args:
            position: Posicion actual (dict de Supabase)
            new_contract: Codigo del nuevo contrato (ej: 'ZCN26')
            roll_price: Precio al que se cierra la posicion vieja
            roll_date: Fecha del roll (YYYY-MM-DD)
            new_entry_price: Precio de entrada del nuevo contrato
                             (default: roll_price)

        Returns:
            (close_update, new_position) - dicts listos para db_risk
        """
        if new_entry_price is None:
            new_entry_price = roll_price

        close_update = {
            'active': False,
            'closed_date': roll_date,
            'closed_price': roll_price,
            'rolled_to': new_contract,
        }

        new_position = {
            'asset': position['asset'],
            'contract': new_contract,
            'direction': position['direction'],
            'nominal': position['nominal'],
            'entry_price': new_entry_price,
            'entry_date': roll_date,
            'active': True,
        }
        if position.get('portfolio_id'):
            new_position['portfolio_id'] = position['portfolio_id']

        return close_update, new_position

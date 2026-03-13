import pandas as pd
import numpy as np
from gestion_de_riesgos.var_engine.var_calculator import VaRCalculator


# Activos soportados y sus unidades de factor
SUPPORTED_ASSETS = {
    'MAIZ': 'TONS',
    'AZUCAR': 'TONS',
    'CACAO': 'TONS',
    'USD': 'USD/COP',
}


def _safe_round(value, decimals=3):
    """Redondea un valor, retorna None si es NaN/None."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return round(value, decimals)


class RiskPortfolio:
    """
    Gestiona el portafolio de riesgos compuesto por:
    - Benchmark (exposicion natural / Super): posiciones de la compania por su operacion.
    - Portafolio GR (gestion de riesgos): coberturas tomadas para mitigar riesgo.

    Genera la tabla consolidada con:
    Posiciones | VaR Diario | Precios | P&G | Information Ratio
    """

    def __init__(
        self,
        benchmark_positions: list[dict],
        gr_positions: list[dict],
        prices_history: pd.DataFrame,
        price_date_start: str,
        price_date_end: str,
    ):
        self.benchmark_positions = {p['asset']: p for p in benchmark_positions}
        self.gr_positions = {p['asset']: p for p in gr_positions}
        self.prices_history = prices_history
        self.price_date_start = price_date_start
        self.price_date_end = price_date_end
        self.var_calculator = VaRCalculator(prices_history)

    def _get_price_at_date(self, date_str: str) -> dict:
        """
        Obtiene precios de cada activo en una fecha especifica.
        Si la fecha exacta no existe, busca el ultimo precio no-NaN
        anterior o igual a la fecha para cada activo individualmente.
        """
        df = self.prices_history.copy()
        df['date'] = pd.to_datetime(df['date'])
        target = pd.to_datetime(date_str)

        before = df[df['date'] <= target]
        if before.empty:
            return {}

        price_cols = [c for c in df.columns if c != 'date']
        result = {}
        for col in price_cols:
            valid = before[before[col].notna()]
            if not valid.empty:
                result[col] = valid[col].iloc[-1]
        return result

    def _calculate_pnl(self, asset: str, position: float, price_start: float, price_end: float) -> float:
        """Calcula P&G = posicion * (precio_fin - precio_inicio)."""
        if price_start is None or price_end is None:
            return 0.0
        if np.isnan(price_start) or np.isnan(price_end):
            return 0.0
        return position * (price_end - price_start)

    def build_risk_table(self) -> list[dict]:
        """
        Construye la tabla de gestion de riesgos.

        Returns:
            Lista de dicts, uno por activo, con la estructura de la tabla.
        """
        var_factors = self.var_calculator.get_latest_var_factors()
        prices_start = self._get_price_at_date(self.price_date_start)
        prices_end = self._get_price_at_date(self.price_date_end)

        rows = []
        totals = {
            'position_super': 0, 'position_gr': 0, 'position_total': 0,
            'var_super': 0, 'var_gr': 0, 'var_total': 0,
            'var_portfolio': 0,
            'pnl_super': 0, 'pnl_gr': 0, 'pnl_total': 0,
        }

        for asset, unit in SUPPORTED_ASSETS.items():
            bench = self.benchmark_positions.get(asset, {})
            gr = self.gr_positions.get(asset, {})

            pos_super = bench.get('position', 0)
            pos_gr = gr.get('position', 0)
            pos_total = pos_super + pos_gr
            weight = bench.get('weight', 0)

            factor = var_factors.get(asset, 0) or 0

            var_super = abs(pos_super) * (factor / 100)
            var_gr = abs(pos_gr) * (factor / 100)
            var_total = abs(pos_total) * (factor / 100)
            var_portfolio = var_total

            p_start = prices_start.get(asset)
            p_end = prices_end.get(asset)

            pnl_super = self._calculate_pnl(asset, pos_super, p_start, p_end)
            pnl_gr = self._calculate_pnl(asset, pos_gr, p_start, p_end)
            pnl_total = pnl_super + pnl_gr

            # Information Ratio = P&G Total / VaR Total (si VaR > 0)
            info_ratio = round(pnl_total / var_total, 2) if var_total > 0 else None

            row = {
                'weight': round(weight * 100, 2),
                'asset': asset,
                'position_super': _safe_round(pos_super, 3),
                'position_gr': _safe_round(pos_gr, 3),
                'position_total': _safe_round(pos_total, 3),
                'var_super': _safe_round(var_super, 3),
                'var_gr': _safe_round(var_gr, 3),
                'var_total': _safe_round(var_total, 3),
                'factor_var_diario': _safe_round(factor, 2),
                'factor_unit': unit,
                'var_portfolio': _safe_round(var_portfolio, 3),
                'price_start': _safe_round(p_start, 4) if p_start is not None else None,
                'price_end': _safe_round(p_end, 4) if p_end is not None else None,
                'pnl_super': _safe_round(pnl_super, 3),
                'pnl_gr': _safe_round(pnl_gr, 3),
                'pnl_total': _safe_round(pnl_total, 3),
                'information_ratio': info_ratio,
            }
            rows.append(row)

            totals['position_super'] += pos_super
            totals['position_gr'] += pos_gr
            totals['position_total'] += pos_total
            totals['var_super'] += var_super
            totals['var_gr'] += var_gr
            totals['var_total'] += var_total
            totals['var_portfolio'] += var_portfolio
            totals['pnl_super'] += pnl_super
            totals['pnl_gr'] += pnl_gr
            totals['pnl_total'] += pnl_total

        total_info_ratio = (
            round(totals['pnl_total'] / totals['var_total'], 2)
            if totals['var_total'] > 0 else None
        )

        total_row = {
            'weight': None,
            'asset': 'Total',
            'position_super': _safe_round(totals['position_super'], 3),
            'position_gr': _safe_round(totals['position_gr'], 3),
            'position_total': _safe_round(totals['position_total'], 3),
            'var_super': _safe_round(totals['var_super'], 3),
            'var_gr': _safe_round(totals['var_gr'], 3),
            'var_total': _safe_round(totals['var_total'], 3),
            'factor_var_diario': None,
            'factor_unit': None,
            'var_portfolio': _safe_round(totals['var_portfolio'], 3),
            'price_start': None,
            'price_end': None,
            'pnl_super': _safe_round(totals['pnl_super'], 3),
            'pnl_gr': _safe_round(totals['pnl_gr'], 3),
            'pnl_total': _safe_round(totals['pnl_total'], 3),
            'information_ratio': total_info_ratio,
        }
        rows.append(total_row)

        return rows

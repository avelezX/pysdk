import numpy as np
import pandas as pd
from scipy.stats import norm


CONFIDENCE_LEVEL = 0.95
ROLLING_WINDOW = 180
Z_SCORE = norm.ppf(CONFIDENCE_LEVEL)


class VaRCalculator:
    """
    Calcula Value at Risk (VaR) parametrico diario usando volatilidad rolling.
    - Ventana rolling: 180 dias
    - Nivel de confianza: 95%
    - Metodo: VaR parametrico (varianza-covarianza)
    """

    def __init__(self, prices: pd.DataFrame, window: int = ROLLING_WINDOW):
        """
        Args:
            prices: DataFrame con columna 'date' y columnas de precios por activo.
                    Ejemplo columnas: ['date', 'MAIZ', 'AZUCAR', 'CACAO', 'USD']
            window: Ventana rolling en dias para calcular volatilidad.
        """
        self.prices = prices.copy()
        self.window = window
        self.z_score = Z_SCORE
        self.returns = None
        self.volatilities = None

    def calculate_returns(self) -> pd.DataFrame:
        """Calcula retornos logaritmicos diarios para cada activo."""
        price_cols = [c for c in self.prices.columns if c != 'date']
        self.returns = np.log(
            self.prices[price_cols] / self.prices[price_cols].shift(1)
        )
        self.returns['date'] = self.prices['date']
        return self.returns

    def calculate_rolling_volatility(self) -> pd.DataFrame:
        """Calcula volatilidad rolling (desviacion estandar) sobre la ventana definida."""
        if self.returns is None:
            self.calculate_returns()

        price_cols = [c for c in self.returns.columns if c != 'date']
        self.volatilities = self.returns[price_cols].rolling(window=self.window, min_periods=30).std()
        self.volatilities['date'] = self.prices['date']
        return self.volatilities

    def calculate_var_factor(self) -> pd.DataFrame:
        """
        Calcula el factor de VaR diario para cada activo.
        Factor VaR = Z * volatilidad_rolling
        """
        if self.volatilities is None:
            self.calculate_rolling_volatility()

        price_cols = [c for c in self.volatilities.columns if c != 'date']
        var_factors = self.volatilities[price_cols] * self.z_score
        var_factors['date'] = self.volatilities['date']
        return var_factors

    def calculate_var(self, positions: dict) -> dict:
        """
        Calcula el VaR diario para un conjunto de posiciones.

        Args:
            positions: dict con la posicion (valor de mercado) por activo.
                      Ejemplo: {'MAIZ': -12585456, 'AZUCAR': -12180561, 'CACAO': -2022003, 'USD': 72773180}

        Returns:
            dict con VaR por activo y VaR total del portafolio.
        """
        var_factors = self.calculate_var_factor()
        price_cols = [c for c in var_factors.columns if c != 'date']

        # Tomar el ultimo factor de VaR disponible
        latest_factors = var_factors[price_cols].iloc[-1]

        result = {}
        total_var = 0

        for asset, position in positions.items():
            if asset in latest_factors.index:
                factor = latest_factors[asset]
                asset_var = abs(position) * factor
                result[asset] = {
                    'position': position,
                    'var_factor': round(factor * 100, 4),
                    'var': round(asset_var, 3)
                }
                total_var += asset_var

        result['total'] = {'var': round(total_var, 3)}
        return result

    def get_latest_var_factors(self) -> dict:
        """Retorna los factores de VaR mas recientes como porcentaje."""
        var_factors = self.calculate_var_factor()
        price_cols = [c for c in var_factors.columns if c != 'date']
        latest = var_factors[price_cols].iloc[-1]
        result = {}
        for col, val in latest.items():
            if pd.isna(val):
                result[col] = 0
            else:
                result[col] = round(val * 100, 4)
        return result

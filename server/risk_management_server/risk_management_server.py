from server.main_server import XerenityFunctionServer, XerenityError, responseHttpOk


class RiskManagementServer(XerenityFunctionServer):

    def __init__(self, body):
        expected = {'filter_date': [str]}

        body_fields = set(expected).difference(body.keys())
        if len(body_fields) > 0:
            raise XerenityError(
                message="Missing fields {}".format(str(body_fields)),
                code=400
            )

        self.filter_date = body['filter_date']
        self.portfolio_id = body.get('portfolio_id', None)
        self.mock = body.get('mock', False)

    def calculate(self):
        """
        Calcula la tabla de gestion de riesgos completa.

        Request body:
            {
                "filter_date": "2026-02-27",
                "portfolio_id": "optional-uuid",
                "mock": false
            }
        """
        if self.mock:
            return self._calculate_mock()

        from gestion_de_riesgos.db_risk import (
            get_risk_prices,
            get_risk_positions,
            get_portfolio_config,
        )
        from gestion_de_riesgos.portfolio import RiskPortfolio
        from datetime import datetime, timedelta

        config = get_portfolio_config(self.portfolio_id)
        price_date_start = config.get('price_date_start', self.filter_date)
        price_date_end = config.get('price_date_end', self.filter_date)
        rolling_window = config.get('rolling_window', 180)

        end_date = datetime.strptime(self.filter_date, '%Y-%m-%d')
        start_date = end_date - timedelta(days=rolling_window + 60)

        prices_df = get_risk_prices(
            initial_date=start_date.strftime('%Y-%m-%d'),
            final_date=self.filter_date
        )

        if prices_df.empty:
            raise XerenityError(
                message="No hay precios historicos disponibles para el rango solicitado",
                code=404
            )

        all_positions = get_risk_positions(self.portfolio_id)

        benchmark_positions = [
            {'asset': p['asset'], 'position': p['position'], 'weight': p.get('weight', 0)}
            for p in all_positions if p.get('position_type') == 'benchmark'
        ]

        gr_positions = [
            {'asset': p['asset'], 'position': p['position']}
            for p in all_positions if p.get('position_type') == 'gr'
        ]

        portfolio = RiskPortfolio(
            benchmark_positions=benchmark_positions,
            gr_positions=gr_positions,
            prices_history=prices_df,
            price_date_start=price_date_start,
            price_date_end=price_date_end,
        )

        risk_table = portfolio.build_risk_table()

        return responseHttpOk(body={
            'risk_table': risk_table,
            'config': {
                'filter_date': self.filter_date,
                'price_date_start': price_date_start,
                'price_date_end': price_date_end,
                'rolling_window': rolling_window,
                'confidence_level': 0.95,
            }
        })

    def _calculate_mock(self):
        """Datos mock basados en la tabla de referencia."""
        risk_table = [
            {
                'weight': 0,
                'asset': 'MAIZ',
                'position_super': -12585.456,
                'position_gr': 0,
                'position_total': -12585.456,
                'var_super': 321.152,
                'var_gr': 0,
                'var_total': 321.152,
                'factor_var_diario': 2.55,
                'factor_unit': 'TONS',
                'var_portfolio': 321.152,
                'price_start': 435.750,
                'price_end': 448.50,
                'pnl_super': 368.249,
                'pnl_gr': 0,
                'pnl_total': 368.249,
                'information_ratio': None,
            },
            {
                'weight': 0,
                'asset': 'AZUCAR',
                'position_super': -12180.561,
                'position_gr': 0,
                'position_total': -12180.561,
                'var_super': 337.483,
                'var_gr': 0,
                'var_total': 337.483,
                'factor_var_diario': 2.77,
                'factor_unit': 'TONS',
                'var_portfolio': 337.483,
                'price_start': 13.84,
                'price_end': 13.89,
                'pnl_super': -44.005,
                'pnl_gr': 0,
                'pnl_total': 44.005,
                'information_ratio': None,
            },
            {
                'weight': 0,
                'asset': 'CACAO',
                'position_super': -2022.003,
                'position_gr': 0,
                'position_total': -2022.003,
                'var_super': 175.878,
                'var_gr': 0,
                'var_total': 175.878,
                'factor_var_diario': 8.70,
                'factor_unit': 'TONS',
                'var_portfolio': 175.878,
                'price_start': 4.162,
                'price_end': 2.798,
                'pnl_super': 662.665,
                'pnl_gr': 0,
                'pnl_total': 662.665,
                'information_ratio': None,
            },
            {
                'weight': 13,
                'asset': 'USD',
                'position_super': 83473.180,
                'position_gr': -10700.000,
                'position_total': 72773.180,
                'var_super': 1345.372,
                'var_gr': 172.456,
                'var_total': 1172.915,
                'factor_var_diario': 1.61,
                'factor_unit': 'USD/COP',
                'var_portfolio': 1345.372,
                'price_start': 3.670,
                'price_end': 3.746,
                'pnl_super': 1678.253,
                'pnl_gr': -190.500,
                'pnl_total': 1487.753,
                'information_ratio': 0.37,
            },
            {
                'weight': None,
                'asset': 'Total',
                'position_super': 56685.160,
                'position_gr': -10700.000,
                'position_total': 45985.160,
                'var_super': 2179.884,
                'var_gr': 172.456,
                'var_total': 2007.428,
                'factor_var_diario': None,
                'factor_unit': None,
                'var_portfolio': 510.859,
                'price_start': None,
                'price_end': None,
                'pnl_super': 1928.664,
                'pnl_gr': -190.500,
                'pnl_total': 1738.164,
                'information_ratio': -0.37,
            },
        ]

        return responseHttpOk(body={
            'risk_table': risk_table,
            'config': {
                'filter_date': self.filter_date,
                'price_date_start': '2026-01-31',
                'price_date_end': '2026-02-27',
                'rolling_window': 180,
                'confidence_level': 0.95,
                'mock': True,
            }
        })

    def benchmark_factors(self):
        """
        Retorna factores para la tabla Benchmark:
        - factor_var_diario: ultimo VaR % por activo
        - price_start: precio inicio del mes anterior
        - price_end: precio fin del mes anterior
        """
        from gestion_de_riesgos.db_risk import get_risk_prices
        from gestion_de_riesgos.var_engine.var_calculator import VaRCalculator
        from datetime import datetime, timedelta
        import pandas as pd
        import math

        ref_date = datetime.strptime(self.filter_date, '%Y-%m-%d')

        # Precio inicio: ultimo dia del mes anterior al mes de ref_date
        first_of_current = ref_date.replace(day=1)
        price_start_date = first_of_current - timedelta(days=1)  # ej: Jan 31

        # Precio fin: la fecha del filtro (ref_date)
        price_end_date = ref_date  # ej: Feb 27

        # Historia suficiente para VaR 180d
        start_history = price_start_date - timedelta(days=250)

        prices_df = get_risk_prices(
            initial_date=start_history.strftime('%Y-%m-%d'),
            final_date=price_end_date.strftime('%Y-%m-%d')
        )

        if prices_df.empty:
            raise XerenityError(
                message="No hay precios historicos disponibles",
                code=404
            )

        # Factor VaR diario (ultimo dia disponible)
        calc = VaRCalculator(prices_df, window=180)
        factors = calc.get_latest_var_factors()

        # Retornos logaritmicos y varianza/covarianza
        import numpy as np
        calc.calculate_returns()
        returns_df = calc.returns.copy()
        prices_df['date'] = pd.to_datetime(prices_df['date'])
        price_cols = [c for c in prices_df.columns if c != 'date']

        # Matriz de covarianza de retornos (ultimos 180 dias)
        returns_only = returns_df[price_cols].dropna()
        if len(returns_only) > 180:
            returns_only = returns_only.tail(180)
        cov_matrix = returns_only.cov()

        # Serializar matriz de covarianza
        cov_dict = {}
        for row_asset in price_cols:
            cov_dict[row_asset] = {}
            for col_asset in price_cols:
                val = cov_matrix.loc[row_asset, col_asset]
                cov_dict[row_asset][col_asset] = round(float(val), 10) if not np.isnan(val) else None

        # Varianza diaria por activo (diagonal de la covarianza)
        daily_variance = {}
        for col in price_cols:
            val = cov_matrix.loc[col, col]
            daily_variance[col] = round(float(val), 10) if not np.isnan(val) else None

        # Matriz de correlacion
        corr_matrix = returns_only.corr()
        corr_dict = {}
        for row_asset in price_cols:
            corr_dict[row_asset] = {}
            for col_asset in price_cols:
                val = corr_matrix.loc[row_asset, col_asset]
                corr_dict[row_asset][col_asset] = round(float(val), 4) if not np.isnan(val) else None

        units = {'MAIZ': 'TONS', 'AZUCAR': 'TONS', 'CACAO': 'TONS', 'USD': 'USD/COP'}

        # Precios hardcoded (31-ene-26 y 27-feb-26)
        hardcoded_prices = {
            'MAIZ':   {'price_start': 435.750, 'price_end': 448.50},
            'AZUCAR': {'price_start': 13.84,   'price_end': 13.89},
            'CACAO':  {'price_start': 4.162,   'price_end': 2.798},
            'USD':    {'price_start': 3670.47,  'price_end': 3745.78},
        }

        def clean(v):
            if v is None or (isinstance(v, float) and math.isnan(v)):
                return None
            return v

        result = {}
        for col in price_cols:
            hc = hardcoded_prices.get(col, {})
            result[col] = {
                'factor_var_diario': clean(factors.get(col, 0)),
                'daily_variance': daily_variance.get(col),
                'price_start': hc.get('price_start'),
                'price_end': hc.get('price_end'),
                'factor_unit': units.get(col, ''),
            }

        return responseHttpOk(body={
            'factors': result,
            'covariance_matrix': cov_dict,
            'correlation_matrix': corr_dict,
            'assets': price_cols,
            'period': {
                'start': price_start_date.strftime('%Y-%m-%d'),
                'end': price_end_date.strftime('%Y-%m-%d'),
            }
        })

    def rolling_var(self):
        """
        Retorna precios historicos y rolling VaR 180d para graficas.

        Response:
            {
                "dates": ["2025-06-01", ...],
                "prices": {"MAIZ": [...], "AZUCAR": [...], ...},
                "rolling_var": {"MAIZ": [...], "AZUCAR": [...], ...}
            }
        """
        from gestion_de_riesgos.db_risk import get_risk_prices
        from gestion_de_riesgos.var_engine.var_calculator import VaRCalculator
        from datetime import datetime, timedelta
        import math

        end_date = datetime.strptime(self.filter_date, '%Y-%m-%d')
        start_date = end_date - timedelta(days=365)

        prices_df = get_risk_prices(
            initial_date=start_date.strftime('%Y-%m-%d'),
            final_date=self.filter_date
        )

        if prices_df.empty:
            raise XerenityError(
                message="No hay precios historicos disponibles",
                code=404
            )

        calc = VaRCalculator(prices_df, window=180)
        var_factors = calc.calculate_var_factor()

        dates = prices_df['date'].tolist()
        price_cols = [c for c in prices_df.columns if c != 'date']

        prices_dict = {}
        rolling_var_dict = {}

        for col in price_cols:
            price_list = prices_df[col].tolist()
            var_list = var_factors[col].tolist()
            prices_dict[col] = [
                None if (v is None or (isinstance(v, float) and math.isnan(v))) else round(v, 4)
                for v in price_list
            ]
            # VaR en USD = var_factor * precio (var_factor ya incluye Z * volatilidad)
            rolling_var_dict[col] = [
                None if (v is None or p is None or
                         (isinstance(v, float) and math.isnan(v)) or
                         (isinstance(p, float) and math.isnan(p)))
                else round(v * p, 2)
                for v, p in zip(var_list, price_list)
            ]

        return responseHttpOk(body={
            'dates': dates,
            'prices': prices_dict,
            'rolling_var': rolling_var_dict,
        })

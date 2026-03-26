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

        self.body = body
        self.filter_date = body['filter_date']
        self.portfolio_id = body.get('portfolio_id', None)
        self.mock = body.get('mock', False)
        self.exposure_params = body.get('exposure_params', None)
        self.confidence_level = body.get('confidence_level', 0.99)

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
        from gestion_de_riesgos.db_risk import get_risk_prices, get_risk_contracts
        from gestion_de_riesgos.var_engine.var_calculator import VaRCalculator
        from datetime import datetime, timedelta
        import pandas as pd
        import math

        ref_date = datetime.strptime(self.filter_date, '%Y-%m-%d')

        # Precio inicio: ultimo dia habil del mes anterior
        # Debe coincidir con la misma logica del frontend (lastBusinessDay)
        # para que price_start de este mes == price_end del mes anterior
        first_of_current = ref_date.replace(day=1)
        last_cal_day_prev = first_of_current - timedelta(days=1)  # ej: Jan 31
        # Retroceder al viernes si cae en fin de semana
        wd = last_cal_day_prev.weekday()  # 0=Mon, 5=Sat, 6=Sun
        if wd == 5:
            price_start_date = last_cal_day_prev - timedelta(days=1)  # Sat -> Fri
        elif wd == 6:
            price_start_date = last_cal_day_prev - timedelta(days=2)  # Sun -> Fri
        else:
            price_start_date = last_cal_day_prev

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
        calc = VaRCalculator(prices_df, window=180, confidence_level=self.confidence_level)
        factors = calc.get_latest_var_factors()

        # Retornos logaritmicos independientes por activo
        import numpy as np
        prices_df['date'] = pd.to_datetime(prices_df['date'])
        price_cols = [c for c in prices_df.columns if c != 'date']

        # Returns independientes: cada activo usa solo sus dias con precio real
        returns_indep = pd.DataFrame(index=prices_df.index)
        for col in price_cols:
            series = prices_df[col].dropna()
            returns_indep[col] = np.log(series / series.shift(1))

        # Ultimas 180 filas del indice (rango temporal)
        returns_window = returns_indep.tail(180)

        # Covarianza pairwise: cada par usa los dias donde ambos tienen return
        cov_matrix = returns_window.cov(min_periods=20)

        # Rango real de datos y observaciones por activo
        cov_start = str(prices_df['date'].iloc[returns_window.index[0]])[:10]
        cov_end = str(prices_df['date'].iloc[returns_window.index[-1]])[:10]
        cov_obs_per_asset = {col: int(returns_window[col].notna().sum()) for col in price_cols}

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

        # Matriz de correlacion (pairwise)
        corr_matrix = returns_window.corr(min_periods=20)
        corr_dict = {}
        for row_asset in price_cols:
            corr_dict[row_asset] = {}
            for col_asset in price_cols:
                val = corr_matrix.loc[row_asset, col_asset]
                corr_dict[row_asset][col_asset] = round(float(val), 4) if not np.isnan(val) else None

        units = {'MAIZ': 'TONS', 'AZUCAR': 'TONS', 'CACAO': 'TONS', 'USD': 'USD/COP'}

        def clean(v):
            if v is None or (isinstance(v, float) and math.isnan(v)):
                return None
            return v

        def find_price(df, col, target_date):
            """Find the closest available price on or before target_date.
            Returns (price, actual_date) tuple."""
            mask = df['date'] <= target_date.strftime('%Y-%m-%d')
            subset = df.loc[mask, ['date', col]].dropna(subset=[col])
            if subset.empty:
                return None, None
            row = subset.iloc[-1]
            actual_date = str(row['date'])[:10]
            return round(float(row[col]), 4), actual_date

        contracts = get_risk_contracts(
            initial_date=start_history.strftime('%Y-%m-%d'),
            final_date=price_end_date.strftime('%Y-%m-%d')
        )

        result = {}
        actual_start_dates = []
        actual_end_dates = []
        for col in price_cols:
            p_start, d_start = find_price(prices_df, col, price_start_date)
            p_end, d_end = find_price(prices_df, col, price_end_date)
            if d_start:
                actual_start_dates.append(d_start)
            if d_end:
                actual_end_dates.append(d_end)
            result[col] = {
                'factor_var_diario': clean(factors.get(col, 0)),
                'daily_variance': daily_variance.get(col),
                'price_start': p_start,
                'price_end': p_end,
                'factor_unit': units.get(col, ''),
                'contract': contracts.get(col),
            }

        # Use actual data dates, not requested dates
        real_start = max(actual_start_dates) if actual_start_dates else price_start_date.strftime('%Y-%m-%d')
        real_end = max(actual_end_dates) if actual_end_dates else price_end_date.strftime('%Y-%m-%d')

        return responseHttpOk(body={
            'factors': result,
            'covariance_matrix': cov_dict,
            'correlation_matrix': corr_dict,
            'assets': price_cols,
            'contracts': contracts,
            'period': {
                'start': real_start,
                'end': real_end,
            },
            'covariance_period': {
                'start': cov_start,
                'end': cov_end,
                'observations': cov_obs_per_asset,
            },
            'confidence_level': self.confidence_level,
            'z_score': round(float(calc.z_score), 4),
        })

    def rolling_var(self):
        """
        Retorna precios historicos y rolling VaR 180d para graficas.

        Response:
            {
                "dates": ["2025-06-01", ...],
                "prices": {"MAIZ": [...], "AZUCAR": [...], ...},
                "rolling_var": {"MAIZ": [...], "AZUCAR": [...], ...},
                "contracts": {"MAIZ": "ZCH26", ...}
            }
        """
        from gestion_de_riesgos.db_risk import get_risk_prices, get_risk_contracts
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

        contracts = get_risk_contracts(
            initial_date=start_date.strftime('%Y-%m-%d'),
            final_date=self.filter_date
        )

        calc = VaRCalculator(prices_df, window=180, confidence_level=self.confidence_level)
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
            'contracts': contracts,
        })

    def collectors_status(self):
        """
        Retorna el estado de los collectors y calendario de contratos.
        Incluye fechas de vencimiento, roll, y contrato front actual.
        """
        from gestion_de_riesgos.collectors.base_collector import (
            COLLECTORS, COMMODITY_CONFIG, JSON_PATHS,
            FuturesJSONCollector, get_collectors_status,
        )

        status = get_collectors_status()

        # Agregar calendario de contratos para cada commodity
        for asset_name in ['MAIZ', 'AZUCAR', 'CACAO']:
            if asset_name in COMMODITY_CONFIG and asset_name in JSON_PATHS:
                collector = FuturesJSONCollector(
                    asset_name, JSON_PATHS[asset_name], COMMODITY_CONFIG[asset_name]
                )
                schedule = collector.get_contract_schedule()
                if asset_name in status:
                    status[asset_name]['schedule'] = schedule

        return responseHttpOk(body=status)

    def update_prices(self):
        """
        Actualiza precios en Supabase leyendo de los JSON locales.
        Usa la nueva logica de roll con fechas de expiracion reales.

        Request body:
            {
                "filter_date": "2026-03-17",
                "assets": ["MAIZ", "AZUCAR", "CACAO", "USD"]  // opcional, default: todos
            }
        """
        from gestion_de_riesgos.collectors.base_collector import (
            COLLECTORS, collect_all,
        )
        from datetime import datetime, timedelta

        end_date = self.filter_date
        ref = datetime.strptime(end_date, '%Y-%m-%d')
        start_date = (ref - timedelta(days=365)).strftime('%Y-%m-%d')

        results = collect_all(start_date, end_date)
        return responseHttpOk(body=results)

    def exposure(self):
        """
        Calcula la exposición en USD por commodity.

        Request body (además de filter_date):
            {
                "filter_date": "2026-03-12",
                "exposure_params": {
                    "proyeccion_azucar": [3157, 3157, ...],  // 12 meses
                    "precio_azucar_cent_lb": 13.89,
                    "factor_crudo_refinado": 1.05,
                    "proyeccion_glucosa": [2277, 2277, ...],
                    "precio_maiz_cent_bu": 442,
                    "base_maiz_cent_bu": 80,
                    "flete_usd_ton": 46,
                    "processing_fee_usd": 263,
                    "proc_fee_cop_kg": 668,
                    "trm": 3800,
                    "factor_maiz_glucosa": 1.495,
                    "proyeccion_cocoa_polvo": [24, 24, ...],
                    "factor_cocoa_polvo": 1.22,
                    "proyeccion_manteca": [13, 13, ...],
                    "factor_manteca": 1.95,
                    "proyeccion_licor": [4, 4, ...],
                    "factor_licor": 1.53,
                    "precio_cocoa_usd_ton": 2798,
                    "proyeccion_bolsa": [151, 151, ...],
                    "proyeccion_envoltura": [138, 138, ...],
                    "precio_empaque_fijo": 21610000,
                    "ventas_intl_usd": 130025826,
                    "ventas_co_usd": 0,
                    "ventas_pe_usd": 42827644
                }
            }
        """
        from gestion_de_riesgos.exposure import calcular_exposicion_total
        from gestion_de_riesgos.db_risk import get_risk_prices, get_risk_contracts
        from datetime import datetime, timedelta

        params = self.exposure_params
        if not params:
            raise XerenityError(
                message="Missing exposure_params in request body",
                code=400
            )

        # Fetch latest futures prices from Supabase
        ref_date = datetime.strptime(self.filter_date, '%Y-%m-%d')
        start_fetch = ref_date - timedelta(days=60)
        prices_df = get_risk_prices(
            initial_date=start_fetch.strftime('%Y-%m-%d'),
            final_date=self.filter_date
        )

        contracts = get_risk_contracts(
            initial_date=start_fetch.strftime('%Y-%m-%d'),
            final_date=self.filter_date
        )

        market_prices = {}
        if not prices_df.empty:
            # Map DB columns to exposure params
            price_map = {
                'AZUCAR': 'precio_azucar_cent_lb',
                'MAIZ': 'precio_maiz_cent_bu',
                'CACAO': 'precio_cocoa_usd_ton',
                'USD': 'trm',
            }
            for db_col, param_key in price_map.items():
                if db_col in prices_df.columns:
                    col_data = prices_df[['date', db_col]].dropna(subset=[db_col])
                    if not col_data.empty:
                        last_row = col_data.iloc[-1]
                        price_val = float(last_row[db_col])
                        price_date = str(last_row['date'])
                        market_prices[param_key] = {
                            'value': round(price_val, 4),
                            'date': price_date,
                            'source': db_col,
                            'contract': contracts.get(db_col),
                        }
                        # Override param with DB price
                        params[param_key] = price_val

        result = calcular_exposicion_total(params)
        result['market_prices'] = market_prices
        return responseHttpOk(body=result)

    # ── Futures Portfolio ──

    def futures_portfolio(self):
        """
        Retorna el portafolio de futuros con P&L calculado.

        Request body:
            {
                "filter_date": "2026-03-25",
                "portfolio_id": "optional-uuid",
                "active_only": true
            }

        Response:
            {
                "portfolio": [
                    {
                        "id": "uuid",
                        "asset": "MAIZ",
                        "contract": "ZCK26",
                        "direction": "SHORT",
                        "nominal": 5,
                        "multiplier": 5000,
                        "entry_price": 435.75,
                        "current_price": 448.50,
                        "valor_t": ...,
                        "valor_t1": ...,
                        "daily_pnl": ...,
                        "pnl_inception": ...,
                        "pnl_month": ...
                    },
                    ...
                    {"asset": "Total", ...}
                ]
            }
        """
        from gestion_de_riesgos.db_risk import get_futures_portfolio, get_risk_prices
        from gestion_de_riesgos.futures_portfolio import FuturesPortfolioCalculator
        from datetime import datetime, timedelta

        active_only = self.body.get('active_only', True)
        positions = get_futures_portfolio(self.portfolio_id, active_only)

        if not positions:
            return responseHttpOk(body={'portfolio': []})

        end_date = datetime.strptime(self.filter_date, '%Y-%m-%d')
        start_date = end_date - timedelta(days=90)
        prices_df = get_risk_prices(
            initial_date=start_date.strftime('%Y-%m-%d'),
            final_date=self.filter_date,
        )

        if prices_df.empty:
            raise XerenityError(
                message="No hay precios historicos disponibles",
                code=404,
            )

        calc = FuturesPortfolioCalculator(positions, prices_df, self.filter_date)
        result = calc.calculate()

        return responseHttpOk(body={'portfolio': result})

    def futures_portfolio_upsert(self):
        """
        Crea o actualiza posiciones de futuros.

        Request body:
            {
                "filter_date": "2026-03-25",
                "positions": [
                    {
                        "asset": "MAIZ",
                        "contract": "ZCK26",
                        "direction": "SHORT",
                        "nominal": 5,
                        "entry_price": 435.75,
                        "entry_date": "2026-01-15"
                    }
                ]
            }
        """
        from gestion_de_riesgos.db_risk import upsert_futures_positions

        records = self.body.get('positions', [])
        if not records:
            raise XerenityError(message="Missing 'positions' in body", code=400)

        upsert_futures_positions(records)
        return responseHttpOk(body={'status': 'ok', 'count': len(records)})

    def futures_portfolio_roll(self):
        """
        Ejecuta un roll de contrato: cierra posicion vieja y abre nueva.

        Request body:
            {
                "filter_date": "2026-03-25",
                "position_id": "uuid-of-old-position",
                "new_contract": "ZCN26",
                "roll_price": 450.25,
                "new_entry_price": 452.00,
                "roll_date": "2026-03-25"
            }
        """
        from gestion_de_riesgos.db_risk import (
            get_futures_position, close_futures_position, upsert_futures_positions,
        )
        from gestion_de_riesgos.futures_portfolio import FuturesPortfolioCalculator

        position_id = self.body.get('position_id')
        new_contract = self.body.get('new_contract')
        roll_price = self.body.get('roll_price')
        new_entry_price = self.body.get('new_entry_price', roll_price)
        roll_date = self.body.get('roll_date', self.filter_date)

        if not all([position_id, new_contract, roll_price]):
            raise XerenityError(
                message="Missing position_id, new_contract, or roll_price",
                code=400,
            )

        old_position = get_futures_position(position_id)
        if not old_position:
            raise XerenityError(
                message=f"Position {position_id} not found",
                code=404,
            )
        if not old_position.get('active'):
            raise XerenityError(
                message="Cannot roll an inactive position",
                code=400,
            )

        close_update, new_pos = FuturesPortfolioCalculator.execute_roll(
            old_position, new_contract, roll_price, roll_date, new_entry_price,
        )

        close_futures_position(
            position_id,
            close_update['closed_date'],
            close_update['closed_price'],
            close_update['rolled_to'],
        )
        upsert_futures_positions([new_pos])

        return responseHttpOk(body={
            'status': 'rolled',
            'closed_position_id': position_id,
            'new_position': new_pos,
        })

    def futures_portfolio_close(self):
        """
        Cierra una posicion de futuros.

        Request body:
            {
                "filter_date": "2026-03-25",
                "position_id": "uuid",
                "closed_price": 448.50,
                "closed_date": "2026-03-25"
            }
        """
        from gestion_de_riesgos.db_risk import get_futures_position, close_futures_position

        position_id = self.body.get('position_id')
        closed_price = self.body.get('closed_price')
        closed_date = self.body.get('closed_date', self.filter_date)

        if not all([position_id, closed_price]):
            raise XerenityError(
                message="Missing position_id or closed_price",
                code=400,
            )

        old = get_futures_position(position_id)
        if not old:
            raise XerenityError(
                message=f"Position {position_id} not found",
                code=404,
            )
        if not old.get('active'):
            raise XerenityError(
                message="Position is already closed",
                code=400,
            )

        close_futures_position(position_id, closed_date, closed_price)
        return responseHttpOk(body={'status': 'closed', 'position_id': position_id})

    def futures_portfolio_delete(self):
        """
        Elimina una posicion de futuros.

        Request body:
            {
                "filter_date": "2026-03-26",
                "position_id": "uuid"
            }
        """
        from gestion_de_riesgos.db_risk import get_futures_position, delete_futures_position

        position_id = self.body.get('position_id')
        if not position_id:
            raise XerenityError(message="Missing position_id", code=400)

        old = get_futures_position(position_id)
        if not old:
            raise XerenityError(
                message=f"Position {position_id} not found",
                code=404,
            )

        delete_futures_position(position_id)
        return responseHttpOk(body={'status': 'deleted', 'position_id': position_id})

    def futures_portfolio_edit(self):
        """
        Edita campos de una posicion de futuros existente.

        Request body:
            {
                "filter_date": "2026-03-26",
                "position_id": "uuid",
                "updates": {
                    "nominal": 3,
                    "entry_price": 450.00,
                    "direction": "LONG",
                    "contract": "ZCN26",
                    "entry_date": "2026-03-01"
                }
            }
        """
        from gestion_de_riesgos.db_risk import get_futures_position, _patch

        position_id = self.body.get('position_id')
        updates = self.body.get('updates', {})

        if not position_id:
            raise XerenityError(message="Missing position_id", code=400)
        if not updates:
            raise XerenityError(message="Missing updates", code=400)

        old = get_futures_position(position_id)
        if not old:
            raise XerenityError(
                message=f"Position {position_id} not found",
                code=404,
            )

        allowed = {'asset', 'contract', 'direction', 'nominal', 'entry_price', 'entry_date'}
        payload = {k: v for k, v in updates.items() if k in allowed}
        if not payload:
            raise XerenityError(message="No valid fields to update", code=400)

        _patch("risk_futures_portfolio", f"id=eq.{position_id}", payload)
        return responseHttpOk(body={'status': 'updated', 'position_id': position_id, 'updated_fields': list(payload.keys())})

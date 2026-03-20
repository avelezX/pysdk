import requests
import pandas as pd
from datetime import datetime, timedelta
from data_collectors.DataCollector import DataCollector


class BcrpCollector(DataCollector):
    """
    Collects economic series from BCRP (Banco Central de Reserva del Peru) REST API.
    API docs: https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/api

    No authentication required. Returns JSON with config + periods arrays.
    Supports up to 10 series per request (same frequency).
    """

    def __init__(self, name='BCRP'):
        super().__init__(name)
        self.session = requests.session()
        self.base_url = 'https://estadisticas.bcrp.gob.pe/estadisticas/series/api'

    def _parse_bcrp_date(self, date_str):
        """
        Parse BCRP date formats:
        - Daily:     '02.Jan.24'  -> 2024-01-02
        - Monthly:   'Jan.24'     -> 2024-01-01
        - Monthly:   'Jan.2024'   -> 2024-01-01  (4-digit year)
        - Quarterly: 'T1.24'      -> 2024-01-01
        """
        try:
            # Daily format: DD.Mon.YY
            return datetime.strptime(date_str, '%d.%b.%y')
        except ValueError:
            pass

        try:
            # Monthly format: Mon.YY (2-digit year)
            return datetime.strptime(date_str, '%b.%y')
        except ValueError:
            pass

        try:
            # Monthly format: Mon.YYYY (4-digit year)
            return datetime.strptime(date_str, '%b.%Y')
        except ValueError:
            pass

        try:
            # Quarterly format: T1.YY or Q1.YY
            parts = date_str.split('.')
            if len(parts) == 2:
                quarter = int(parts[0].replace('T', '').replace('Q', ''))
                year = int(parts[1])
                if year < 100:
                    year += 2000
                month = (quarter - 1) * 3 + 1
                return datetime(year, month, 1)
        except (ValueError, IndexError):
            pass

        raise ValueError(f'Cannot parse BCRP date: {date_str}')

    def get_series(self, series_codes, from_date=None, to_date=None):
        """
        Fetch one or more series from BCRP API.

        Args:
            series_codes: list of BCRP series codes (e.g. ['PD04637PD', 'PD04638PD'])
            from_date: start date as 'YYYY-M-D' (daily) or 'YYYY-M' (monthly)
            to_date: end date, same format

        Returns:
            dict with {series_code: DataFrame(fecha, valor)} for each series
        """
        codes_str = '-'.join(series_codes)

        url_parts = [self.base_url, codes_str, 'json']
        if from_date:
            url_parts.append(from_date)
        if to_date:
            url_parts.append(to_date)
        url_parts.append('ing')

        url = '/'.join(url_parts)

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f'Error fetching BCRP series {codes_str}: {e}')
            return {}

        config_series = data.get('config', {}).get('series', [])
        periods = data.get('periods', [])

        if not config_series or not periods:
            print(f'No data returned for {codes_str}')
            return {}

        results = {}
        for idx, code in enumerate(series_codes):
            rows = []
            for period in periods:
                value_str = period['values'][idx] if idx < len(period['values']) else 'n.d.'
                if value_str == 'n.d.' or value_str is None or value_str == '':
                    continue

                try:
                    fecha = self._parse_bcrp_date(period['name'])
                    valor = float(value_str)
                    rows.append({'fecha': fecha.strftime('%Y-%m-%d'), 'valor': valor})
                except (ValueError, TypeError) as e:
                    print(f'Skipping invalid record {period["name"]}: {e}')
                    continue

            results[code] = pd.DataFrame(rows)

        return results

    def get_stock_price(self, symbol, from_date=None, to_date=None):
        """
        Override DataCollector interface. Fetches a single series.
        Returns DataFrame with columns: id_serie, fecha, valor
        """
        if from_date is None:
            from_date = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
        if to_date is None:
            to_date = datetime.today().strftime('%Y-%m-%d')

        results = self.get_series([symbol], from_date, to_date)
        return results.get(symbol, pd.DataFrame())

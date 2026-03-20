import requests
import pandas as pd
from datetime import datetime, timedelta
from data_collectors.DataCollector import DataCollector


class CryptoCompareCollector(DataCollector):
    """
    Collects daily crypto price data from CryptoCompare API.
    No API key required for basic usage.
    Endpoint: https://min-api.cryptocompare.com/data/v2/histoday
    """

    def __init__(self, name):
        super().__init__(name)
        self.session = requests.session()
        self.base_url = 'https://min-api.cryptocompare.com/data/v2/histoday'

    def get_price(self, from_symbol: str, to_symbol: str = 'USD', history_days: int = 10):
        """
        Fetch daily OHLCV data for a crypto pair.

        Args:
            from_symbol: Crypto symbol (BTC, ETH, SOL, etc.)
            to_symbol: Quote currency (USD, EUR, COP, etc.)
            history_days: Number of days to fetch

        Returns:
            DataFrame with columns: time, value, volume, currency
        """
        try:
            response = self.session.get(
                self.base_url,
                params={
                    'fsym': from_symbol,
                    'tsym': to_symbol,
                    'limit': history_days,
                },
                timeout=30
            )

            data = response.json()

            if data.get('Response') != 'Success' or not data.get('Data', {}).get('Data'):
                print(f'Error fetching {from_symbol}:{to_symbol}: {data.get("Message", "Unknown error")}')
                return pd.DataFrame()

            records = data['Data']['Data']

            rows = []
            for record in records:
                if record['close'] <= 0:
                    continue

                timestamp = datetime.utcfromtimestamp(record['time'])
                rows.append({
                    'time': timestamp,
                    'value': record['close'],
                    'volume': record.get('volumefrom', 0),
                    'currency': f'{from_symbol}:{to_symbol}',
                })

            df = pd.DataFrame(rows)
            return df

        except Exception as e:
            print(f'Error fetching {from_symbol}:{to_symbol}: {e}')
            return pd.DataFrame()

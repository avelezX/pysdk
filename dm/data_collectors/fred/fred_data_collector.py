import requests
import json
from data_collectors.DataCollector import DataCollector
import pandas_datareader as pdr
from datetime import datetime, timedelta


class Fred(DataCollector):
    def __init__(self):
        super().__init__(name='fred')

        self.has_intra_day_prices = False

        # self.api_key = '0ecb1545aa91670f6b492c475b020601'

        # self.fred_url = 'https://api.stlouisfed.org/fred/series'

    def get_stock_price(self, symbol: str, from_date=(datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d'),
                        to_date=datetime.today().strftime('%Y-%m-%d')):
        dframe = pdr.get_data_fred(symbol, from_date, to_date)

        dframe.rename(columns={symbol: 'Close'}, inplace=True)

        return dframe

    def get_multiple_stock_price(self, symbol: list, date):
        pass

import pandas as pd
from datetime import datetime,timedelta

# https://github.com/ranaroussi/yfinance/issues/1700
import appdirs as ad
ad.user_cache_dir = lambda *args: "/tmp"

import yfinance as yf

from data_collectors.DataCollector import DataCollector

from pandas_datareader import data as pdr


class YahooExtractor(DataCollector):

    def __init__(self):
        super().__init__(name='yahoo')
        yf.pdr_override()

        self.has_intra_day_prices = False

    def get_stock_price(self, symbol: str, from_date=(datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d'),
                        to_date=datetime.today().strftime('%Y-%m-%d')):

        frame = pdr.get_data_yahoo(symbol, from_date)
        return frame.reset_index()

    def get_multiple_stock_price(self, symbol: list, date):
        return pdr.get_data_yahoo(symbol, date)


from datetime import datetime
from datetime import datetime, timedelta
import pandas as pd


class DataCollector:

    def __init__(self, name):
        self.pure_dataframe = pd.DataFrame(None)
        self.has_intra_day_prices: bool = False
        self.name = name

    def get_stock_price(self, symbol: str, from_date=(datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d'),
                        to_date=datetime.today().strftime('%Y-%m-%d')):
        pass

    def get_multiple_stock_price(self, symbol: list, date):
        pass

import requests
from datetime import datetime, timedelta
from data_collectors.DataCollector import DataCollector
import pytz
import pandas as pd
import io


class EuropeanCentralBank(DataCollector):
    FREQUENCIES = {
        "daily": "D",
        "hourly": "H"
    }

    def __init__(self, name):
        super().__init__(name)

        self.session = requests.session()

        self.base_url = 'https://data-api.ecb.europa.eu/'

        self.currency_url = self.base_url + 'service/data/EXR/{}'

    def get_price(self, from_symbol: str, from_date=datetime.today(),
                  to_date=datetime.today().strftime('%Y-%m-%d'), to_symbol: str = "EUR", history_days=2):
        base_search = self.build_retrieval(
            from_currency=from_symbol,
            to_currency=to_symbol,
            frequency="daily"
        )

        dtime = datetime.now()

        yesterday = dtime - timedelta(days=history_days)

        timezone = pytz.timezone("UTC")

        dtzone = timezone.localize(yesterday)

        response = self.session.get(
            self.currency_url.format(base_search),
            params={"format": "csvdata", "updatedAfter": str(dtzone).replace(" ", "T")}
        )

        buffer = io.StringIO(response.content.decode())

        df = pd.read_csv(filepath_or_buffer=buffer)

        df = df[['TIME_PERIOD', 'OBS_VALUE']]

        df.rename(columns={'TIME_PERIOD': 'time', 'OBS_VALUE': 'value'}, inplace=True)

        df['currency'] = '{}:{}'.format(from_symbol, to_symbol)
        df['volume'] = 0

        return df

    def build_retrieval(self, from_currency, to_currency, frequency):
        if frequency not in self.FREQUENCIES:
            assert False, "{} not in {}".format(frequency, self.FREQUENCIES.keys())

        return "{}.{}.{}.SP00.A".format(
            self.FREQUENCIES[frequency],
            from_currency,
            to_currency
        )

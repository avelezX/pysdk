import json

import requests
import pandas as pd
from data_collectors.DataCollector import DataCollector
from datetime import date


class ForwardRateCollector(DataCollector):

    def __init__(self, name):
        super().__init__(name)

        self.session = requests.session()

        self.base_url = 'https://pysdk.fly.dev/fwd_rates'

    def get_ibr_quotes(self, ibr_quotes, interval_tenor):
        today = date.today()

        body = {
            "ibr_quotes": ibr_quotes,
            "interval_tenor": interval_tenor,
            "start_date": today.strftime("%Y-%m-%dT%H:%M:%S")
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        data = self.session.get(url=self.base_url, json=body, headers=headers)

        if data.status_code in range(200, 204):
            return pd.DataFrame(data.json())

        raise Exception(data.json())

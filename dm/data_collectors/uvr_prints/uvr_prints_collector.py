import json

import requests
import pandas as pd
from data_collectors.DataCollector import DataCollector
from datetime import date


class IbrPrintsCollector(DataCollector):

    def __init__(self, name):
        super().__init__(name)

        self.session = requests.session()

        self.base_url = 'https://pysdk.fly.dev/{}'

        self.uvr_prints = 'uvr_prints'

        self.cpi_implicit = 'cpi_implicit'

    def get_ibr_quotes(self, uvr, cbr, tes_table, last_cpi, last_cpi_lag_0, col_tes):
        today = date.today()

        body = {
            'uvr': uvr,
            'cbr': cbr,
            'tes_table': tes_table,
            'last_cpi': last_cpi,
            'inflation_lag_0': last_cpi_lag_0,
            'calc_date': today.strftime("%Y-%m-%dT%H:%M:%S"),
            'col_tes': col_tes
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        data = self.session.get(url=self.base_url.format(self.uvr_prints), json=body, headers=headers)

        if data.status_code in range(200, 204):
            return pd.DataFrame(data.json())

        raise Exception(data.json())

    def get_cpi_implicit(self, uvr, cbr, tes_table, last_cpi, last_cpi_lag_0, col_tes):
        today = date.today()

        body = {
            'uvr': uvr,
            'cbr': cbr,
            'tes_table': tes_table,
            'last_cpi': last_cpi,
            'inflation_lag_0': last_cpi_lag_0,
            'calc_date': today.strftime("%Y-%m-%dT%H:%M:%S"),
            'col_tes': col_tes
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        data = self.session.get(url=self.base_url.format(self.cpi_implicit), json=body, headers=headers)

        if data.status_code in range(200, 204):
            return pd.DataFrame(data.json())

        raise Exception(data.json())

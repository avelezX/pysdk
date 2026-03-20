import sys

# sys.path.insert(0,'/Users/avelezxerenity/.pyenv/versions/xerenity/lib/python3.10/site-packages')
sys.path.append('/Users/avelezxerenity/Documents/GitHub/xerenity-dm')

import requests
import pandas as pd
from data_collectors.dtcc.dtcc_collector import DttcColelctor


class trmCollector(DttcColelctor):
    def __init__(self):
        super().__init__(name='fic')

        self.has_intra_day_prices = False

        self.periodicity = 'd'

        self.base_url = "https://www.datos.gov.co/resource/mcec-87by.json"

        self.base_query = "SELECT `valor` as __select_alias__, `unidad` as __select_alias1__, `vigenciadesde` as __select_alias2__, `vigenciahasta` as __select_alias3__ ORDER BY `vigenciahasta` DESC LIMIT {}"

    def get_raw_data(self, days=100):

        params = {
            "$query": self.base_query.format(days)
        }
        return requests.get(self.base_url, params=params)

    def clean_raw_data_1(self, row_data_json):

        if row_data_json.status_code == 200:
            # Append the dataframe
            df = pd.DataFrame(row_data_json.json())
            df.rename(columns={"__select_alias__": "value", "__select_alias2__": "time"}, inplace=True)
            df['currency'] = 'USD:COP'
            df['volume'] = 0
            df['time'] = df['time'].str.replace('T', ' ')
            df.drop(columns=["__select_alias1__", "__select_alias3__"], axis=1, inplace=True)
            return df
        else:
            print(row_data_json.status_code)

import requests
import pandas as pd
import io
from datetime import datetime, timedelta
from data_collectors.DataCollector import DataCollector


class BanrepDataCollector(DataCollector):

    def __init__(self):
        super().__init__(name='banrep')

        self.session = requests.session()

        self.base_url = 'https://totoro.banrep.gov.co/analytics/saw.dll?Download'

        """
        https://totoro.banrep.gov.co/analytics/saw.dll?
        Download&
        Format=csv&
        Extension=.csv&
        BypassCache=true&
        lang=es&
        NQUser=publico&
        NQPassword=publico123&
        Path=/shared/Series Estadísticas_T/1. PIB/1. 2015/1.4 PIB_Precios constantes grandes ramas de actividades economicas_anual&
        SyncOperation=1"
        """

    def create_params(self, symbol):
        params = {

            "Format": "csv",
            "Extension": ".csv",
            "BypassCache": True,
            "lang": "es",
            "NQUser": "publico",
            "NQPassword": "publico123",
            "Path": symbol,
            "SyncOperation": "1"
        }

        return params

    def get_stock_price(self, symbol: str, columns = None, from_date=datetime.today(),
                        to_date=datetime.today().strftime('%Y-%m-%d')):

        params = self.create_params(symbol=symbol)

        header_dict = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0"
        }

        response = self.session.get(url=self.base_url, params=params, stream=True, headers=header_dict)

        print(response.status_code)

        if response.status_code in range(200, 210):
            buffer = io.StringIO(response.text)
            df = pd.read_csv(filepath_or_buffer=buffer)
            df = df.iloc[:,:]
            print(df.head())
            return df
        else:
            print(response.status_code)

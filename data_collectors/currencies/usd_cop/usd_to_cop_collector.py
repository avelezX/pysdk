import json
import re
import requests
import pandas as pd
from html.parser import HTMLParser
from datetime import datetime, timedelta
from data_collectors.DataCollector import DataCollector


class UsToCopCollector(DataCollector):

    def __init__(self, name):
        super().__init__(name)

        self.session = requests.session()

        self.base_url = 'https://dolar.set-icap.com/'
        self.proxy_url = 'https://proxy.set-icap.com'

    def get_stock_price(self, symbol: str, from_date=datetime.today(),
                        to_date=datetime.today().strftime('%Y-%m-%d')):

        grafico_url = "{}/seticap/api/graficos/graficoMoneda/".format(self.proxy_url)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "U2FsdGVkX19DSC/UgOTmKKFT71EmflbBX3tiljxmNpmMcLRZSwNlQCKxUXoN3QpJQ/f7lOA8X41400fnR5G7wA=="
        }

        body = {"fecha": "{}-{}-{}".format(from_date.year, from_date.month, from_date.day), "moneda": 1, "delay": "1"}

        grafico = self.session.post(url=grafico_url, json=body, headers=headers)

        response = grafico.json()

        all_datasets = None

        # 2023-12-28 00:00:00 Postgress timestamps
        if 'status' in response and 'result' in response:

            try:
                for resultados in response['result']:

                    for key in resultados.keys():
                        all_datasets = str(resultados[key])

                        all_datasets = re.sub('\s', '', all_datasets)

                        all_datasets = re.sub('(\d*):(\d*):(\d*)', '"\g<1>-\g<2>-\g<3>"', all_datasets)

                        all_datasets = re.sub('(\w+)', '"\g<1>"', all_datasets)

                        all_datasets = re.sub('=', ':', all_datasets)

                        all_datasets = all_datasets.replace('"-"', ":")

                        all_datasets = all_datasets.replace('""', '"')

                        all_datasets = all_datasets.replace("'", "")

                        all_datasets = all_datasets.replace('"."', ".")

                        all_datasets = all_datasets.replace('"data":{', "{")

                        all_datasets = all_datasets.replace('"("', "")

                        all_datasets = all_datasets.replace('")', '"')
            except Exception as e:
                print(e)

        data_frame: pd.DataFrame = pd.DataFrame()
        if all_datasets is not None:
            all_datasets = json.loads(all_datasets)

            if 'datasets' in all_datasets:
                full_data = {
                    "value": [],
                    "volume": [],
                    "time": pd.to_datetime(["{}T{}".format(body['fecha'], i) for i in all_datasets['labels']])
                }

                for data in all_datasets['datasets']:
                    if "precios" in str(data['label']).lower():
                        full_data['value'] = data['data']

                    if "montos" in str(data['label']).lower():
                        full_data['volume'] = data['data']

                data_frame = pd.DataFrame(full_data)
                data_frame['currency'] = self.name

        return data_frame

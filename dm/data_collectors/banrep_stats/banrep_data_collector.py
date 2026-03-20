import pandas as pd
from data_collectors.WebDataCollector import WebDataCollector
from datetime import datetime, timedelta
import requests

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from data_collectors.banrep_stats.web_pages.Estadisticas import StatsPages


class BanrepSeries:
    TASA_POLITICA_MONETARIA = '1'


class BanrepCollector(WebDataCollector):
    def __init__(self):
        super().__init__(name='banrep')

        self.has_intra_day_prices = False

        self.series = BanrepSeries()

        self.banrep_url = 'https://totoro.banrep.gov.co/estadisticas-economicas/DataSerie?={}'

        self.central_page = 'https://totoro.banrep.gov.co/estadisticas-economicas/'

    def quit_browser(self):
        self.driver.quit()

    def session_set_up(self, name: str):

        try:

            stats = StatsPages(driver=self.driver.driver)

            stats.open()

            stats.click_in_catalogo()

            if stats.find_series(series_name=name):

                WebDriverWait(self.driver.driver, 30).until(EC.url_contains('charts'))

                cookies = self.driver.driver.get_cookies()

                print("Copying cookies")
                for cookie in cookies:
                    print("Copying {}".format(cookie['name']))
                    self.session.cookies.set(cookie['name'], cookie['value'])
            else:
                print('No row found')

            print("Quiting web driver")
        except Exception as e:
            print(e)

    def get_stock_price(self, symbol: str, from_date=(datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d'),
                        to_date=datetime.today().strftime('%Y-%m-%d')):
        self.session_set_up(name=symbol)
        self.pure_dataframe = pd.DataFrame(self.get_series_assert_name(symbol))

    def get_series_assert_name(self, name):
        response = self.session.get(self.banrep_url.format(1))

        response_json = response.json()

        data = []

        downloaded_obj = None
        for key, value in response_json.items():
            if 'data' in response_json[key]:
                if 'nombre' in response_json[key]:
                    if name in response_json[key]['nombre']:
                        data = response_json[key]['data']

                        print(response_json[key]['nombre'])
                        downloaded_obj = response_json[key]
                        break

        assert downloaded_obj is not None, "No data was found"
        assert name in downloaded_obj['nombre'], "Name does not match to desired"

        content = []

        for data_point in data:
            content.append(
                {
                    "fecha": str(datetime.fromtimestamp(data_point[0] / 1000)),
                    "valor": float(data_point[1])
                }
            )

        return content

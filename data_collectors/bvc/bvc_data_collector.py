import pandas as pd
from data_collectors.WebDataCollector import WebDataCollector
from datetime import datetime, timedelta
import requests

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from data_collectors.banrep_stats.web_pages.Estadisticas import StatsPages

from data_collectors.bvc.web_pages.Operaciones import BvcOperaciones


class BvcCollector(WebDataCollector):
    def __init__(self):
        super().__init__(name='bvc')

        self.has_intra_day_prices = False

        self.banrep_url = 'https://rest.bvc.com.co/market-information/rf/lvl-3/operation?filters[marketDataRfPub][tradeDate]=2023-10-10&filters[marketDataRfPub][symbol]={}&filters[marketDataRfPub][segment]=A2A'

        self.central_page = 'https://www.bvc.com.co/renta-fija-deuda-publica-segmento-publico/{}?tab=resumen'

    def quit_browser(self):
        self.driver.quit()

    def session_set_up(self, name: str):
        try:

            bvc = BvcOperaciones(self.driver.driver)

            bvc.open(self.central_page.format(name.lower()))

            cookies = self.driver.driver.get_cookies()
            agent = self.driver.driver.execute_script("return navigator.userAgent")
            print(agent)

            print("Copying cookies")
            for cookie in cookies:
                print("-- {} {}".format(cookie['name'], cookie['value']))
                self.session.cookies.set(cookie['name'], cookie['value'])

        except Exception as e:
            print(e)

    def get_stock_price(self, symbol: str, from_date=(datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d'),
                        to_date=datetime.today().strftime('%Y-%m-%d')):
        self.session_set_up(name=symbol)
        print(self.get_series_assert_name(symbol))

        # self.pure_dataframe = pd.DataFrame(self.get_series_assert_name(symbol))

    def get_series_assert_name(self, name):
        # print(self.banrep_url.format(name))
        response = self.session.options(url=self.banrep_url.format(name))
        print(response.text)
        self.session.headers['Accept'] = 'application/json'
        self.session.headers['access-control-allow-credentials'] = 'true'
        self.session.headers['access-control-allow-origin'] = '*'
        self.session.headers['content-type'] = 'application/json; charset=utf-8'
        print(self.session.headers)
        response = self.session.get(url=self.banrep_url.format(name))
        print(response.json())

        return response

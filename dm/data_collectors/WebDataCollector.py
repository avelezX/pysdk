import requests
from data_collectors.DataCollector import DataCollector
from data_collectors.web_scrapper.CreateBrowser import WebDriver


class WebDataCollector(DataCollector):

    def __init__(self, name):
        super().__init__(name)
        self.driver = WebDriver(name)
        self.session = requests.session()

    def session_set_up(self, name: str):
        pass

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from data_collectors.web_scrapper.Pages.WebPage import WebPage
from selenium.webdriver.chrome.webdriver import WebDriver


class BvcOperaciones(WebPage):

    def __init__(self, driver: WebDriver):
        super().__init__(driver)
        self.url = 'https://www.bvc.com.co/mercado-local-en-linea?tab=renta-fija_deuda-publica-segmento-publico'

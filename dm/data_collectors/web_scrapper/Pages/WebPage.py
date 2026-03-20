from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class WebPage:

    def __init__(self, driver: WebDriver):
        self.driver = driver

        self.url = ''

    def open(self, url=None):
        if url is None:
            url = self.url

        self.driver.get(url)

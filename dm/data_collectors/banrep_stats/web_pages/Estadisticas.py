from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from data_collectors.web_scrapper.Pages.WebPage import WebPage
from selenium.webdriver.chrome.webdriver import WebDriver


class StatsPages(WebPage):

    def __init__(self, driver: WebDriver):
        super().__init__(driver)
        self.url = 'https://totoro.banrep.gov.co/estadisticas-economicas/'

    def click_in_catalogo(self):
        search_by = (By.ID, 'idBtnCatalogoSeries')

        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(search_by))

        button = self.driver.find_element(*search_by)

        button.click()

    def find_series(self, series_name) -> bool:
        search_expression = "//tr[.//td[contains(text(),'{}')]]".format(series_name)

        print('Searching for {}'.format(search_expression))

        rows = self.driver.find_elements(by=By.XPATH, value=search_expression)

        print('Found {}'.format(len(rows)))

        row = None

        all_rows=[]
        for element in rows:
            row_children = element.find_elements(By.XPATH, '*')
            for child in row_children:
                print(child)
                if series_name in child.text:
                    row = element
                    break

        if row is not None:
            print('Row found!!!')

            p_row = row.find_element(By.CLASS_NAME, 'columnP')

            clickables = p_row.find_elements(By.XPATH, '*')

            for a in clickables:
                a.click()
                break

            return True

        return False

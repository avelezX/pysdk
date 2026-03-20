import requests
from data_collectors.web_scrapper.CreateBrowser import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from data_collectors.banrep_stats.banrep_data_collector import BanrepCollector

web = WebDriver()

#search_for = 'Tasa de política monetaria'
search_for = 'Tasa de política monetaria'

try:
    web.driver.get('https://totoro.banrep.gov.co/estadisticas-economicas/')

    search_by = (By.ID, 'idBtnCatalogoSeries')

    WebDriverWait(web.driver, 10).until(EC.element_to_be_clickable(search_by))

    button = web.driver.find_element(*search_by)

    web.safe_click(element=button)

    all_table_rows = web.driver.find_elements(by=By.TAG_NAME, value='tr')

    row = None
    for element in all_table_rows:
        row_children = element.find_elements(By.XPATH, '*')
        for child in row_children:
            if search_for == child.text:
                row = element
                break

    print("------------------------------------------------------------------------------------")
    print(row)
    print("------------------------------------------------------------------------------------")

    if row is not None:
        print("-----------Starting actions-----------")

        p_row = row.find_element(By.CLASS_NAME, 'columnP')

        clickables = p_row.find_elements(By.XPATH, '*')

        for a in clickables:
            a.click()
            break

        WebDriverWait(web.driver, 30).until(EC.url_contains('charts'))

        cookies = web.driver.get_cookies()

        session = requests.session()

        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        rep = BanrepCollector(session=session)

        rep.get_stock_price(symbol=search_for)

        print(rep.pure_dataframe)


except Exception as e:
    print(e)

web.quit()

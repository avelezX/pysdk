from selenium.webdriver.remote.file_detector import LocalFileDetector
from selenium import webdriver


class WebDriver:

    def __init__(self, session_name: str):
        url, options = self.browser_stack()

        self.driver = webdriver.Remote(
            command_executor=url
            , options=options
        )
        self.driver.file_detector = LocalFileDetector()

        self.driver.maximize_window()

    def local_host(self):
        options = webdriver.ChromeOptions()

        options.add_argument('--headless')
        options.add_argument("--no-sandbox")

        options.headless = True

        return 'http://127.0.0.1:4444', options

    def lamdba_test(self, session_name='WebReader'):
        options = webdriver.ChromeOptions()

        options.browser_version = "119.0"
        options.platform_name = "Windows 10"

        lt_options = {
            "username": "svelez",
            "accessKey": "5wGj1eiIdqKYDQYNGiiKlOupxaC4AXK8jQ1E70pnEavx7O1AHA",
            "project": session_name,
            "w3c": True,
            "plugin": "python-python"
        }

        options.set_capability('LT:Options', lt_options)

        return 'hub.lambdatest.com/wd/hub', options

    def grid_lastic(self):
        options = webdriver.ChromeOptions()
        desired_capabilities = {
            "browserName": "chrome",
            "browserVersion": "latest",
            "video": "True",
            "platform": "LINUX",
            "platformName": "windows",
        }

        options.set_capability("browserName", "chrome")
        options.set_capability("browserVersion", "latest")
        options.set_capability("platformName", "LINUX")

        return 'https://oAccmG5O1XgFLIQFHfe78OkGqj8vW2Rb:tUdFq9kiWqNxYt3wz7txLE42N3nAV5Bf@xerenity-hub.gridlastic.com/wd/hub', options

    def quit(self):
        self.driver.quit()

    def sauce_labs(self):
        options = webdriver.ChromeOptions()
        options.browser_version = 'latest'
        options.platform_name = 'Windows 11'
        sauce_options = {}
        sauce_options['username'] = 'santiagovelezsaf_n8Zazf'
        sauce_options['accessKey'] = 'vWBZaFoQqLksEmqefNr3'
        sauce_options['build'] = 'selenium-build-2M8XM'
        sauce_options['name'] = '<your test name>'
        options.set_capability('sauce:options', sauce_options)

        return "https://ondemand.us-west-1.saucelabs.com:443/wd/hub", options

    def browser_stack(self):
        desired_cap = {
            "os": "Windows",
            "osVersion": "10",
            "buildName": "Banrep Collection",
            "sessionName": "Banrep Collection",
            "userName": 'santiagovelezsaf_n8Zazf',
            "accessKey": 'vWBZaFoQqLksEmqefNr3'
        }
        options = webdriver.ChromeOptions()
        options.set_capability('bstack:options', desired_cap)

        return "https://hub.browserstack.com/wd/hub", options

    def safe_click(self, element):
        self.driver.execute_script("arguments[0].click();", element)

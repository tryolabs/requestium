import shutil

import pytest
import selenium
from selenium.webdriver.common.by import By

import requestium

chrome_webdriver_path = shutil.which("chromedriver")

chrome_webdriver = selenium.webdriver.chrome.webdriver.WebDriver()
firefox_webdriver = selenium.webdriver.firefox.webdriver.WebDriver()

session_parameters = [
    {"webdriver_path": chrome_webdriver_path},
    {"webdriver_path": chrome_webdriver_path, "headless": True},
    {"driver": chrome_webdriver},
    {"driver": firefox_webdriver},
]


@pytest.mark.parametrize("params", session_parameters)
def test_simple_page_load(params) -> None:
    with requestium.Session(**params) as session:
        session.driver.get("http://the-internet.herokuapp.com")
        session.driver.ensure_element(By.ID, "content")

        title = session.driver.title
        heading = session.driver.find_element(By.XPATH, '//*[@id="content"]/h1')

        assert title == "The Internet"
        assert heading.text == "Welcome to the-internet"

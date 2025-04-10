import shutil
import tempfile

import pytest
import selenium.webdriver
from selenium.webdriver.common.by import By

from requestium import Session

chrome_webdriver_path = shutil.which("chromedriver")


def create_chrome_session(headless=False):
    chrome_options = selenium.webdriver.ChromeOptions()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
    return Session(webdriver_path=chrome_webdriver_path, browser_options=chrome_options)


session_factories = {
    "chrome": lambda: create_chrome_session(),
    "chrome_headless": lambda: create_chrome_session(headless=True),
    "firefox": lambda: Session(driver=selenium.webdriver.Firefox()),
    "requestium_driver": lambda: Session(driver=selenium.webdriver.Chrome()),
}


@pytest.fixture(params=session_factories.keys())
def session(request):
    session = session_factories[request.param]()
    yield session
    session.driver.quit()


def test_simple_page_load(session):
    session.driver.get("http://the-internet.herokuapp.com")
    session.driver.ensure_element(By.ID, "content")
    title = session.driver.title
    heading = session.driver.find_element(By.XPATH, '//*[@id="content"]/h1')
    assert title == "The Internet"
    assert heading.text == "Welcome to the-internet"

import contextlib
import shutil

import pytest
import selenium.webdriver
from requestium import Session


@contextlib.contextmanager
def create_chrome_session(headless=False):
    chrome_options = selenium.webdriver.ChromeOptions()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    session = Session(
        webdriver_path=shutil.which("chromedriver"), browser_options=chrome_options
    )
    try:
        yield session
    finally:
        session.driver.quit()


session_factories = {
    "chrome": lambda: create_chrome_session(),
    "chrome_headless": lambda: create_chrome_session(headless=True),
    "firefox": lambda: Session(driver=selenium.webdriver.Firefox()),
    "requestium_driver": lambda: Session(driver=selenium.webdriver.Chrome()),
}


@pytest.fixture(params=["chrome", "chrome_headless"])
def session(request):
    with create_chrome_session(headless=(request.param == "chrome_headless")) as s:
        yield s


def test_deprecation_warning_for_ensure_element_locators_with_underscores(session):
    session.driver.get("http://the-internet.herokuapp.com")
    with pytest.warns(
        DeprecationWarning,
        match="Support for locator strategy names with underscores is deprecated",
    ):
        session.driver.ensure_element("class_name", "no-js")

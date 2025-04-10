import shutil
import tempfile

import pytest
import selenium.webdriver
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


def test_deprecation_warning_for_ensure_element_locators_with_underscores(session):
    session.driver.get("http://the-internet.herokuapp.com")
    with pytest.warns(
        DeprecationWarning,
        match="Support for locator strategy names with underscores is deprecated",
    ):
        session.driver.ensure_element("class_name", "no-js")

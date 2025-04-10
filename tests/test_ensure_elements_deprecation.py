import shutil
import pytest
from selenium import webdriver
from requestium import Session

chrome_webdriver_path = shutil.which("chromedriver")

session_factories = {
    "chrome": lambda: Session(webdriver_path=chrome_webdriver_path),
    "chrome_headless": lambda: Session(
        webdriver_path=chrome_webdriver_path, headless=True
    ),
    "firefox": lambda: Session(driver=webdriver.Firefox()),
    "requestium_driver": lambda: Session(driver=webdriver.Chrome()),
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

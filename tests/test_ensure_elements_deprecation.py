import shutil

import pytest
from selenium import webdriver

import requestium

chrome_webdriver_path = shutil.which("chromedriver")

chrome_webdriver = webdriver.Chrome()
firefox_webdriver = webdriver.Firefox()

session_parameters = [
    {"webdriver_path": chrome_webdriver_path},
    {"webdriver_path": chrome_webdriver_path, "headless": True},
    {"driver": chrome_webdriver},
    {"driver": firefox_webdriver},
]


@pytest.fixture(params=session_parameters)
def session(request):
    session = requestium.Session(**request.param)
    yield session
    session.driver.close()


def test_deprecation_warning_for_ensure_element_locators_with_underscores(session):
    session.driver.get("http://the-internet.herokuapp.com")
    with pytest.warns(DeprecationWarning):
        session.driver.ensure_element("class_name", "no-js")
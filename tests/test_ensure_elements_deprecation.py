import shutil
from typing import Any

from collections.abc import Generator

import pytest
import selenium

import requestium
from requestium import Session

chrome_webdriver_path = shutil.which("chromedriver")

chrome_webdriver = selenium.webdriver.chrome.webdriver.WebDriver()
firefox_webdriver = selenium.webdriver.firefox.webdriver.WebDriver()

session_parameters = [
    {"webdriver_path": chrome_webdriver_path},
    {"webdriver_path": chrome_webdriver_path, "headless": True},
    {"driver": chrome_webdriver},
    {"driver": firefox_webdriver},
]


@pytest.fixture(params=session_parameters)
def session(request) -> Generator[Session, Any, None]:
    session = requestium.Session(**request.param)
    yield session
    session.driver.quit()


def test_deprecation_warning_for_ensure_element_locators_with_underscores(session) -> None:
    session.driver.get("http://the-internet.herokuapp.com")
    with pytest.warns(DeprecationWarning):
        session.driver.ensure_element("class_name", "no-js")

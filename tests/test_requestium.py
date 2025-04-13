import shutil
from typing import Any

from collections.abc import Generator

import pytest
import selenium
from selenium.common import InvalidCookieDomainException
from selenium.webdriver.common.by import By

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


def test_simple_page_load(session) -> None:
    session.driver.get("http://the-internet.herokuapp.com")
    session.driver.ensure_element(By.ID, "content")
    title = session.driver.title
    heading = session.driver.find_element(By.XPATH, '//*[@id="content"]/h1')
    assert title == "The Internet"
    assert heading.text == "Welcome to the-internet"


def test_copy_user_agent_from_driver(session) -> None:
    """Ensure that requests user-agent header has been changed after calling session.copy_user_agent_from_driver()"""
    pre_copy_requests_useragent = session.headers["user-agent"]
    assert pre_copy_requests_useragent and pre_copy_requests_useragent != ""

    session.driver.get("http://example.com")
    session.copy_user_agent_from_driver()
    post_copy_requests_useragent = session.headers["user-agent"]

    assert post_copy_requests_useragent != pre_copy_requests_useragent


def test_transfer_session_cookies_to_driver_no_domain_error(session) -> None:
    with pytest.raises(
        InvalidCookieDomainException,
        match="Trying to transfer cookies to selenium without specifying a domain and without having visited any page in the current session",
    ):
        session.transfer_session_cookies_to_driver()

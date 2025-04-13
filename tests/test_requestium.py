import shutil

import pytest
import selenium
from selenium.common import InvalidCookieDomainException
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


def test__start_chrome_driver() -> None:
    with requestium.Session() as session:
        session._start_chrome_browser()
        session.driver.get("http://the-internet.herokuapp.com")
        title = session.driver.title
        assert title == "The Internet"


def test__start_chrome_driver_options_typeerror() -> None:
    invalid_webdriver_options = {"arguments": "invalid_string"}
    with (
        requestium.Session(webdriver_options=invalid_webdriver_options) as session,
        pytest.raises(
            TypeError,
            match=f"'arguments' option must be a list, but got {type(invalid_webdriver_options['arguments']).__name__}",
        ),
    ):
        session._start_chrome_browser()


@pytest.mark.parametrize("params", session_parameters)
def test_copy_user_agent_from_driver(params) -> None:
    """Ensure that requests user-agent header has been changed after calling session.copy_user_agent_from_driver()"""
    with requestium.Session(**params) as session:
        pre_copy_requests_useragent = session.headers["user-agent"]
        assert pre_copy_requests_useragent and pre_copy_requests_useragent != ""

        session.driver.get("http://the-internet.herokuapp.com")
        session.copy_user_agent_from_driver()
        post_copy_requests_useragent = session.headers["user-agent"]

        assert post_copy_requests_useragent != pre_copy_requests_useragent


@pytest.mark.parametrize("params", session_parameters)
def test_transfer_session_cookies_to_driver_no_domain_error(params) -> None:
    with (
        requestium.Session(**params) as session,
        pytest.raises(
            InvalidCookieDomainException,
            match="Trying to transfer cookies to selenium without specifying a domain and without having visited any page in the current session",
        ),
    ):
        session.transfer_session_cookies_to_driver()

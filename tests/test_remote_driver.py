"""
A requestium Session driving a webdriver.Remote, as used with a Selenium Grid.

No grid is needed: chromedriver is itself a W3C WebDriver server, so a locally started ChromeService is a
perfectly good remote endpoint (https://github.com/tryolabs/requestium/issues/31).
"""

from collections.abc import Generator

import pytest
from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.driver_finder import DriverFinder
from selenium.webdriver.remote.webelement import WebElement

import requestium.requestium

from .conftest import LocalServer, chrome_options

COOKIE = {"name": "remote_cookie", "value": "from-remote", "domain": "example.com", "path": "/"}


@pytest.fixture(scope="module")
def remote_session(server: LocalServer) -> Generator[requestium.Session, None, None]:
    options = chrome_options(server, headless=True)
    driver = None
    try:
        # Selenium Manager finds (or downloads) chromedriver, the same as webdriver.Chrome would
        service = webdriver.ChromeService(executable_path=DriverFinder(webdriver.ChromeService(), options).get_driver_path())
        service.start()
    except (WebDriverException, ValueError) as e:
        pytest.skip(f"chromedriver is not available for a remote session: {e!s}")
    try:
        driver = webdriver.Remote(command_executor=service.service_url, options=options)
    except WebDriverException as e:
        service.stop()
        pytest.skip(f"Chrome is not available for a remote session: {e!s}")

    session = requestium.Session(driver=driver)
    session.proxies.update(server.proxies)
    try:
        yield session
    finally:
        driver.quit()
        service.stop()


@pytest.fixture
def clean_remote_session(remote_session: requestium.Session) -> requestium.Session:
    remote_session.cookies.clear()
    remote_session.driver.delete_all_cookies()
    return remote_session


def test_driver_is_remote_with_requestium_methods(remote_session: requestium.Session) -> None:
    assert isinstance(remote_session.driver, webdriver.Remote)
    assert callable(remote_session.driver.ensure_element)
    assert callable(remote_session.driver.xpath)


def test_ensure_element(remote_session: requestium.Session, example_url: str) -> None:
    remote_session.driver.get(example_url)

    element = remote_session.driver.ensure_element(By.ID, "test-header", "visible")
    assert isinstance(element, WebElement)
    assert element.text == "Test Header 2"
    assert remote_session.driver.ensure_element_by_css_selector("button", "clickable") is not None


def test_driver_parsing(remote_session: requestium.Session, example_url: str) -> None:
    remote_session.driver.get(example_url)

    assert remote_session.driver.xpath("//h1/text()").get() == "Test Header 1"
    assert remote_session.driver.css("a::text").getall() == ["Test Link 1", "Test Link 2"]
    assert remote_session.driver.re_first(r"Test Paragraph (\d)") == "1"


def test_transfer_session_cookies_to_driver(clean_remote_session: requestium.Session) -> None:
    session = clean_remote_session
    session.get(f"http://example.com/set-cookie?name={COOKIE['name']}&value={COOKIE['value']}")

    session.transfer_session_cookies_to_driver()

    driver_cookies = session.driver.get_cookies()
    assert [(c["name"], c["value"]) for c in driver_cookies] == [(COOKIE["name"], COOKIE["value"])]
    sent = session.driver.execute_async_script("fetch('/echo').then((r) => r.json()).then(arguments[0]);")["cookies"]
    assert sent == f"{COOKIE['name']}={COOKIE['value']}"


def test_transfer_driver_cookies_to_session(clean_remote_session: requestium.Session) -> None:
    session = clean_remote_session
    session.driver.ensure_add_cookie(dict(COOKIE))

    session.transfer_driver_cookies_to_session()

    assert {cookie.name: cookie.value for cookie in session.cookies} == {COOKIE["name"]: COOKIE["value"]}
    assert session.get("http://example.com/echo").json()["cookies"] == f"{COOKIE['name']}={COOKIE['value']}"

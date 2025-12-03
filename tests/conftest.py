import contextlib
from collections.abc import Generator
from typing import TYPE_CHECKING, cast

import pytest
from _pytest.fixtures import FixtureRequest
from selenium import webdriver
from selenium.common import WebDriverException

import requestium

if TYPE_CHECKING:
    from requestium.requestium_mixin import DriverMixin

# ruff: noqa FBT003


@pytest.fixture(scope="module")
def example_html() -> str:
    return """
    <html>
        <head><title>The Internet</title></head>
        <body>
            <h1>Test Header 1</h1>
            <h2 id="test-header">Test Header 2</h2>
            <h3 class="test-header-3">Test Header 3</h3>
            <p class="body-text">Test Paragraph 1</p>
            <p><a href="example.com" name="link-paragraph">Test Link 1</a></p>
            <p><a href="example.com">Test Link 2</a></p>
        </body>
    </html>
    """


def _create_chrome_driver(headless: bool) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if headless:
        options.add_argument("--headless=new")
    return webdriver.Chrome(options=options)


def _create_firefox_driver(headless: bool) -> webdriver.Firefox:
    options = webdriver.FirefoxOptions()
    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)
    options.set_preference("browser.cache.offline.enable", False)
    options.set_preference("network.http.use-cache", False)
    if headless:
        options.add_argument("--headless")
    return webdriver.Firefox(options=options)


@pytest.fixture(
    params=["chrome-headless", "chrome", "firefox-headless", "firefox"],
    scope="module",
)
def session(request: FixtureRequest) -> Generator[requestium.Session, None, None]:
    driver_type = request.param
    browser, _, mode = driver_type.partition("-")
    headless = mode == "headless"

    driver: webdriver.Chrome | webdriver.Firefox
    if browser == "chrome":
        driver = _create_chrome_driver(headless)
    elif browser == "firefox":
        driver = _create_firefox_driver(headless)
    else:
        msg = f"Unknown driver type: {browser}"
        raise ValueError(msg)

    session = requestium.Session(driver=cast("DriverMixin", driver))
    yield session

    with contextlib.suppress(WebDriverException, OSError):
        driver.quit()

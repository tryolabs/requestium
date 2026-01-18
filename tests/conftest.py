import contextlib
from collections.abc import Generator
from typing import TYPE_CHECKING, cast

import pytest
import urllib3.exceptions
from _pytest.fixtures import FixtureRequest
from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.wait import WebDriverWait

import requestium

if TYPE_CHECKING:
    from requestium.requestium_mixin import DriverMixin


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
            <button>Click Me</button>
            <p><a href="example.com" name="link-paragraph">Test Link 1</a></p>
            <p><a href="example.com">Test Link 2</a></p>
        </body>
    </html>
    """


def _create_chrome_driver(*, headless: bool) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if headless:
        options.add_argument("--headless=new")

    try:
        driver = webdriver.Chrome(options=options)
        WebDriverWait(driver, 5).until(EC.number_of_windows_to_be(1))
        return driver
    except (urllib3.exceptions.ReadTimeoutError, TimeoutError, WebDriverException) as e:
        error_msg = f"Chrome driver initialization failed: {e}"
        raise RuntimeError(error_msg) from e


def _create_firefox_driver(*, headless: bool) -> webdriver.Firefox:
    options = webdriver.FirefoxOptions()
    options.set_preference("browser.cache.disk.enable", value=False)
    options.set_preference("browser.cache.memory.enable", value=False)
    options.set_preference("browser.cache.offline.enable", value=False)
    options.set_preference("network.http.use-cache", value=False)
    if headless:
        options.add_argument("--headless")

    try:
        driver = webdriver.Firefox(options=options)
        WebDriverWait(driver, 5).until(EC.number_of_windows_to_be(1))
        return driver
    except (urllib3.exceptions.ReadTimeoutError, TimeoutError, WebDriverException) as e:
        error_msg = f"Firefox driver initialization failed: {e}"
        raise RuntimeError(error_msg) from e


@pytest.fixture(
    params=["chrome-headless", "chrome", "firefox-headless", "firefox"],
    scope="module",
)
def session(request: FixtureRequest) -> Generator[requestium.Session, None, None]:
    driver_type = request.param
    browser, _, mode = driver_type.partition("-")
    headless = mode == "headless"

    driver: webdriver.Chrome | webdriver.Firefox

    try:
        if browser == "chrome":
            driver = _create_chrome_driver(headless=headless)
        elif browser == "firefox":
            driver = _create_firefox_driver(headless=headless)
        else:
            msg = f"Unknown driver type: {browser}"
            raise ValueError(msg)

        assert driver.name in browser
        session = requestium.Session(driver=cast("DriverMixin", driver))
        assert session.driver.name in browser

    try:
        _ = session.driver.current_url
        _ = session.driver.window_handles
    except WebDriverException as e:
        if "Browsing context has been discarded" not in str(e):
            raise

        try:
            session.driver.switch_to.new_window("tab")
        except WebDriverException:
            pytest.skip("Browser context discarded and cannot be recovered")

        yield session

    except RuntimeError as e:
        # Driver creation failed - skip all tests using this session
        pytest.skip(str(e))

    finally:
        with contextlib.suppress(WebDriverException, OSError, Exception):
            driver.quit()

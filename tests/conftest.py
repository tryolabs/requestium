import contextlib
from collections.abc import Generator
from typing import TYPE_CHECKING, cast

import pytest
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


@pytest.fixture(
    params=[
        "chrome-headless",
        "chrome",
        "firefox-headless",
        "firefox",
    ],
    scope="module",
)
def session(request) -> Generator[requestium.Session]:  # noqa: ANN001
    driver_type = request.param

    driver: webdriver.Chrome | webdriver.Firefox
    if "chrome" in driver_type:
        chrome_options: webdriver.ChromeOptions = webdriver.ChromeOptions()
        chrome_options.add_argument("--no-sandbox")  # Helps when running on Github Actions
        chrome_options.add_argument("--disable-dev-shm-usage")  # Helps when running on Github Actions
        if driver_type == "chrome-headless":
            chrome_options.add_argument("--headless=new")
        driver = webdriver.Chrome(options=chrome_options)
    elif "firefox" in driver_type:
        firefox_options: webdriver.FirefoxOptions = webdriver.FirefoxOptions()
        firefox_options.set_preference("browser.cache.disk.enable", False)
        firefox_options.set_preference("browser.cache.memory.enable", False)
        firefox_options.set_preference("browser.cache.offline.enable", False)
        firefox_options.set_preference("network.http.use-cache", False)
        if driver_type == "firefox-headless":
            firefox_options.add_argument("--headless")
        driver = webdriver.Firefox(options=firefox_options)
    else:
        msg = f"Unknown driver type: {driver_type}"
        raise ValueError(msg)

    session = requestium.Session(driver=cast("DriverMixin", driver))
    yield session

    # Close all windows and end the session
    with contextlib.suppress(WebDriverException, OSError):
        driver.quit()

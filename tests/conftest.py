# import os
# import shutil
from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING, cast

import pytest
from selenium import webdriver
from selenium.common.exceptions import WebDriverException

import requestium

if TYPE_CHECKING:
    from requestium.requestium_mixin import DriverMixin


@pytest.fixture
def example_html() -> str:
    return """
    <html>
        <head><title>The Internet</title></head>
        <body><h1>Test Page</h1></body>
    </html>
    """


def create_firefox_driver(*, headless: bool = False, max_retries: int = 3) -> webdriver.Firefox | None:
    """Create Firefox driver with retry logic."""
    for attempt in range(max_retries):
        try:
            options = webdriver.FirefoxOptions()
            if headless:
                options.add_argument("--headless")

            service = webdriver.FirefoxService(timeout=300)
            return webdriver.Firefox(options=options, service=service)
        except (WebDriverException, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2)  # Brief delay before retry
    return None


@pytest.fixture(
    params=[
        "chrome-headless",
        "chrome",
        # "chrome-custom-path",
        "firefox-headless",
        "firefox",
    ]
)
def session(request):  # noqa: ANN001, ANN201
    driver_type = request.param

    if driver_type == "chrome-headless":
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        driver = webdriver.Chrome(options=options)
    elif driver_type == "chrome":
        driver = webdriver.Chrome()
    # elif driver_type == "chrome-custom-path":
    #     chromedriver_name = "chromedriver"
    #     custom_path = shutil.which(chromedriver_name)
    #     assert custom_path, f"'{chromedriver_name}' not found in PATH."
    #     assert os.path.exists(custom_path), f"Custom chromedriver not found at {custom_path}."
    #     driver = webdriver.Chrome(service=webdriver.ChromeService(executable_path=custom_path))
    elif driver_type == "firefox-headless":
        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        driver = webdriver.Firefox(options=options)
    elif driver_type == "firefox":
        driver = create_firefox_driver(headless=False)
    else:
        msg = f"Unknown driver type: {driver_type}"
        raise ValueError(msg)

    session = requestium.Session(driver=cast("DriverMixin", driver))
    yield session

    # Close all windows and end the session
    with contextlib.suppress(WebDriverException, OSError):
        driver.quit()

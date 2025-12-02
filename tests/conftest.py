# import os
# import shutil
import contextlib
import os
from typing import TYPE_CHECKING, cast

import pytest
from selenium import webdriver
from selenium.common import WebDriverException

import requestium

if TYPE_CHECKING:
    from requestium.requestium_mixin import DriverMixin


@pytest.fixture
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
        # "chrome-custom-path",
        "firefox-headless",
        pytest.param("firefox", marks=pytest.mark.skipif(os.getenv("CI") == "true", reason="Non-headless Firefox unreliable in CI")),
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
        driver = webdriver.Firefox()
    else:
        msg = f"Unknown driver type: {driver_type}"
        raise ValueError(msg)

    session = requestium.Session(driver=cast("DriverMixin", driver))
    yield session

    # Close all windows and end the session
    with contextlib.suppress(WebDriverException, OSError):
        driver.quit()

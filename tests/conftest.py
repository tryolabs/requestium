# import os
# import shutil
from typing import TYPE_CHECKING, cast

import pytest
from selenium import webdriver

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
        driver = webdriver.Firefox()
    else:
        msg = f"Unknown driver type: {driver_type}"
        raise ValueError(msg)

    with requestium.Session(driver=cast("DriverMixin", driver)) as session:
        yield session

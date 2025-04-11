import shutil

import pytest
import selenium.webdriver
import requestium


chrome_webdriver_path = shutil.which("chromedriver")

session_parameters = [
    {"webdriver_path": chrome_webdriver_path},
    {"webdriver_path": chrome_webdriver_path, "headless": True},
    {"driver": "chrome"},
    {"driver": "firefox"},
]


@pytest.fixture(params=session_parameters)
def session(request):
    params = request.param.copy()  # Make a copy so we don't mutate the original

    if params.get("driver") == "chrome":
        params["driver"] = selenium.webdriver.chrome.webdriver.WebDriver()
    elif params.get("driver") == "firefox":
        params["driver"] = selenium.webdriver.firefox.webdriver.WebDriver()

    with requestium.Session(**params) as s:
        yield s

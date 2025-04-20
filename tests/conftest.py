# import os
# import shutil

import pytest
from selenium import webdriver

import requestium


@pytest.fixture(
    params=[
        "chrome",
        "chrome-headless",
        "firefox",
        "firefox-headless",
        # "chrome-custom-path",
    ]
)
def session(request):
    driver_type = request.param

    if driver_type == "chrome":
        driver = webdriver.Chrome()
    elif driver_type == "chrome-headless":
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        driver = webdriver.Chrome(options=options)
    elif driver_type == "firefox":
        driver = webdriver.Firefox()
    elif driver_type == "firefox-headless":
        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        driver = webdriver.Firefox(options=options)
    # elif driver_type == "chrome-custom-path":
    #     chromedriver_name = "chromedriver"
    #     custom_path = shutil.which(chromedriver_name)
    #     assert custom_path, f"'{chromedriver_name}' not found in PATH."
    #     assert os.path.exists(custom_path), f"Custom chromedriver not found at {custom_path}."
    #     driver = webdriver.Chrome(service=webdriver.ChromeService(executable_path=custom_path))
    else:
        msg = f"Unknown driver type: {driver_type}"
        raise ValueError(msg)

    with requestium.Session(driver=driver) as session:
        yield session

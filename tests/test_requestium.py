import shutil

import pytest
import selenium.webdriver
from selenium.webdriver.common.by import By

import requestium

chrome_webdriver_path = shutil.which("chromedriver")
session_parameters = [
    {"webdriver_path": chrome_webdriver_path},
    {"webdriver_path": chrome_webdriver_path, "headless": True},
    {"driver": selenium.webdriver.Chrome()},
    {"driver": selenium.webdriver.Firefox()},
]


@pytest.fixture(params=session_parameters)
def session(request):
    session = requestium.Session(**request.param)
    yield session
    session.driver.close()


def test_simple_page_load(session):
    session.driver.get("http://the-internet.herokuapp.com")
    session.driver.ensure_element(By.ID, "content")
    title = session.driver.title
    heading = session.driver.find_element(By.XPATH, '//*[@id="content"]/h1')
    assert title == "The Internet"
    assert heading.text == "Welcome to the-internet"

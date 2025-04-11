import pytest
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By


def test_simple_page_load(session):
    session.driver.get("https://the-internet.herokuapp.com")
    session.driver.ensure_element(By.ID, "content")
    with pytest.raises(TimeoutException):
        session.driver.ensure_element(By.ID, "thingthatdoesntexist")
    title = session.driver.title
    heading = session.driver.find_element(By.XPATH, '//*[@id="content"]/h1')
    assert title == "The Internet"
    assert heading.text == "Welcome to the-internet"

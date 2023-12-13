import pytest
import selenium
import shutil

import requestium


chrome_webdriver_path = shutil.which('chromedriver')

chrome_webdriver = selenium.webdriver.chrome.webdriver.WebDriver()
firefox_webdriver = selenium.webdriver.firefox.webdriver.WebDriver()


session_parameters = [
    {'webdriver_path': chrome_webdriver_path},
    {'webdriver_path': chrome_webdriver_path, 'headless': True},
    {'driver': chrome_webdriver},
    {'driver': firefox_webdriver},
]


@pytest.fixture(params=session_parameters)
def session(request):
    session = requestium.Session(**request.param)
    yield session
    session.driver.close()


def test_simple_page_load(session):
    session.driver.get('http://the-internet.herokuapp.com')
    session.driver.ensure_element('id', 'content')
    title = session.driver.title
    heading = session.driver.find_element('xpath', '//*[@id="content"]/h1')
    assert title == 'The Internet'
    assert heading.text == 'Welcome to the-internet'

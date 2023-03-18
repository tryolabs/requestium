import pytest
import selenium

import requestium


chrome_webdriver = selenium.webdriver.chrome.webdriver.WebDriver()
firefox_webdriver = selenium.webdriver.firefox.webdriver.WebDriver()


session_parameters = [
    {'webdriver_path': 'chromedriver'},
    {'webdriver_path': 'chromedriver', 'headless': True},
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

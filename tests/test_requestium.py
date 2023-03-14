import warnings

import pytest

import requestium


session_parameters = [
    {'webdriver_path': 'chromedriver', 'browser': 'chrome'},
    {'webdriver_path': 'chromedriver', 'browser': 'chrome-headless'},
]


@pytest.fixture(params=session_parameters)
def session(request):
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    session = requestium.Session(**request.param)
    yield session
    session.driver.close()


def test_simple_page_load(session):
    session.driver.get('http://the-internet.herokuapp.com')
    session.driver.ensure_element_by_id('content')
    title = session.driver.title
    heading = session.driver.find_element_by_xpath('//*[@id="content"]/h1')
    assert title == 'The Internet'
    assert heading.text == 'Welcome to the-internet'

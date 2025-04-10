import contextlib
import shutil
import tempfile

import pytest
import selenium.webdriver
from selenium.webdriver.common.by import By

from requestium import Session


@contextlib.contextmanager
def create_chrome_session(headless=False):
    with tempfile.TemporaryDirectory() as tmp_profile_dir:
        chrome_options = selenium.webdriver.ChromeOptions()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument(f"--user-data-dir={tmp_profile_dir}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        session = Session(
            webdriver_path=shutil.which("chromedriver"), browser_options=chrome_options
        )
        try:
            yield session
        finally:
            session.driver.quit()


session_factories = {
    "chrome": lambda: create_chrome_session(),
    "chrome_headless": lambda: create_chrome_session(headless=True),
    "firefox": lambda: Session(driver=selenium.webdriver.Firefox()),
    "requestium_driver": lambda: Session(driver=selenium.webdriver.Chrome()),
}


@pytest.fixture(params=["chrome", "chrome_headless"])
def session(request):
    with create_chrome_session(headless=(request.param == "chrome_headless")) as s:
        yield s


def test_simple_page_load(session):
    session.driver.get("http://the-internet.herokuapp.com")
    session.driver.ensure_element(By.ID, "content")
    title = session.driver.title
    heading = session.driver.find_element(By.XPATH, '//*[@id="content"]/h1')
    assert title == "The Internet"
    assert heading.text == "Welcome to the-internet"

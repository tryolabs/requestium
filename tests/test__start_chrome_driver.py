import contextlib

import pytest
from selenium.common import WebDriverException
from selenium.webdriver.common.by import By

import requestium.requestium


@pytest.mark.parametrize(
    "headless",
    [
        False,
        True,
    ],
    ids=["headless=false", "headless=true"],
)
def test__start_chrome_driver(session: requestium.Session, example_html: str, headless: bool) -> None:  # noqa: FBT001
    session._start_chrome_browser(headless=headless)
    session.driver.get(f"data:text/html,{example_html}")
    session.driver.ensure_element(By.TAG_NAME, "h1")

    assert session.driver.title == "The Internet"


def test__start_chrome_driver_webdriver_options(example_html: str) -> None:
    webdriver_options = {"arguments": ["headless=new"]}
    session = requestium.Session(webdriver_options=webdriver_options)
    session.driver.get(f"data:text/html,{example_html}")
    session.driver.ensure_element(By.TAG_NAME, "h1")

    assert session.driver.title == "The Internet"

    with contextlib.suppress(WebDriverException, OSError):
        session.driver.quit()


def test__start_chrome_driver_webdriver_options_typeerror() -> None:
    invalid_webdriver_options = {"arguments": "invalid_string"}
    with (
        requestium.Session(webdriver_options=invalid_webdriver_options) as session,
        pytest.raises(
            TypeError,
            match=f"'arguments' option must be a list, but got {type(invalid_webdriver_options['arguments']).__name__}",
        ),
    ):
        session._start_chrome_browser()

import contextlib
from pathlib import Path

import pytest
from selenium.common import WebDriverException
from selenium.webdriver.common.by import By

import requestium.requestium

from .conftest import validate_session


@pytest.mark.parametrize(
    "headless",
    [
        None,
        False,
        True,
    ],
    ids=["no_headless_arg", "headless=false", "headless=true"],
)
def test_initialize_session_without_explicit_driver(example_html: str, headless: bool) -> None:  # noqa: FBT001
    session = requestium.Session(headless=headless)
    validate_session(session)
    session.driver.get(f"data:text/html,{example_html}")
    session.driver.ensure_element(By.TAG_NAME, "h1")

    assert session.driver.title == "The Internet"

    with contextlib.suppress(WebDriverException, OSError):
        session.driver.quit()


def test_initialize_session_with_webdriver_options(example_html: str) -> None:
    session = requestium.Session(webdriver_options={"arguments": ["headless=new"]})
    validate_session(session)
    session.driver.get(f"data:text/html,{example_html}")
    session.driver.ensure_element(By.TAG_NAME, "h1")

    assert session.driver.title == "The Internet"

    with contextlib.suppress(WebDriverException, OSError):
        session.driver.quit()


def test_initialize_session_with_experimental_options(example_html: str) -> None:
    session = requestium.Session(webdriver_options={"experimental_options": {"useAutomationExtension": False}})
    validate_session(session)
    session.driver.get(f"data:text/html,{example_html}")
    session.driver.ensure_element(By.TAG_NAME, "h1")

    assert session.driver.title == "The Internet"

    with contextlib.suppress(WebDriverException, OSError):
        session.driver.quit()


def test_initialize_session_with_webdriver_prefs(example_html: str) -> None:
    session = requestium.Session(webdriver_options={"prefs": {"plugins.always_open_pdf_externally": True}})
    validate_session(session)
    session.driver.get(f"data:text/html,{example_html}")
    session.driver.ensure_element(By.TAG_NAME, "h1")

    assert session.driver.title == "The Internet"

    with contextlib.suppress(WebDriverException, OSError):
        session.driver.quit()


def test_initialize_session_with_extension(example_html: str) -> None:
    test_extension_path = Path(__file__).parent / "resources/test_extension.crx"
    session = requestium.Session(webdriver_options={"extensions": [str(test_extension_path)]})
    validate_session(session)
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
            match="'arguments' option must be a list, but got str",
        ),
    ):
        session._start_chrome_browser()

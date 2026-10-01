import contextlib
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import pytest
from selenium.common import WebDriverException
from selenium.webdriver.common.by import By

import requestium.requestium

from .conftest import validate_session

SessionFactory = Callable[..., requestium.Session]


@pytest.fixture
def make_session() -> Generator[SessionFactory, None, None]:
    """Create sessions that start their own Chrome, and quit every browser afterwards."""
    sessions: list[requestium.Session] = []

    def _make_session(**kwargs: Any) -> requestium.Session:  # noqa: ANN401
        session = requestium.Session(**kwargs)
        sessions.append(session)
        return session

    yield _make_session

    for session in sessions:
        if session._driver:
            with contextlib.suppress(WebDriverException, OSError):
                session._driver.quit()


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"headless": None},
        {"headless": False},
        {"headless": True},
        {"webdriver_options": {"arguments": ["headless=new"]}},
        {"webdriver_options": {"experimental_options": {"useAutomationExtension": False}}},
        {"webdriver_options": {"prefs": {"plugins.always_open_pdf_externally": True}}},
        {"webdriver_options": {"extensions": [str(Path(__file__).parent / "resources/test_extension.crx")]}},
    ],
    ids=["no_args", "no_headless_arg", "headless=false", "headless=true", "arguments", "experimental_options", "prefs", "extension"],
)
def test_initialize_session_without_explicit_driver(make_session: SessionFactory, example_url: str, kwargs: dict[str, Any]) -> None:
    session = make_session(**kwargs)
    validate_session(session)
    session.driver.get(example_url)
    session.driver.ensure_element(By.TAG_NAME, "h1")

    assert session.driver.title == "The Internet"


def test_session_driver_is_created_lazily(make_session: SessionFactory) -> None:
    session = make_session(headless=True)
    assert session._driver is None

    assert session.driver is session.driver
    assert session._driver is not None


def test_default_timeout_reaches_driver_created_by_session(make_session: SessionFactory) -> None:
    session = make_session(headless=True, default_timeout=1.5)

    assert session.driver.default_timeout == 1.5


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

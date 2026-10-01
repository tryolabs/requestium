import contextlib
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import pytest
from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

import requestium.requestium
from requestium.requestium import DriverMixin, RequestiumResponse
from requestium.requestium_session import _mixin_class

from .conftest import LocalServer, chrome_options, own_chrome_session, validate_session

SessionFactory = Callable[..., requestium.Session]


@pytest.fixture
def make_session() -> Generator[SessionFactory, None, None]:
    """Create sessions that start their own Chrome, and quit every browser afterwards."""
    sessions: list[requestium.Session] = []

    def _make_session(**kwargs: Any) -> requestium.Session:  # noqa: ANN401
        session = own_chrome_session(**kwargs)
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


def driver_is_dead(driver: WebDriver) -> bool:
    return not driver.service.is_connectable()  # type: ignore[attr-defined]


def test_close_quits_lazily_started_chrome() -> None:
    session = own_chrome_session(headless=True)
    driver = session.driver
    assert not driver_is_dead(driver)
    session.close()
    assert driver_is_dead(driver)
    assert session._driver is None


def test_close_then_driver_access_starts_fresh_chrome() -> None:
    session = own_chrome_session(headless=True)
    first = session.driver
    session.close()
    second = session.driver
    try:
        assert second is not first
        assert second.execute_script("return 1 + 1;") == 2
    finally:
        session.close()


def test_context_manager_quits_driver() -> None:
    with own_chrome_session(headless=True) as session:
        driver = session.driver
        assert not driver_is_dead(driver)
    assert driver_is_dead(driver)


def test_close_without_driver_does_not_start_one() -> None:
    session = own_chrome_session(headless=True)
    session.close()
    assert session._driver is None


def test_close_twice_is_harmless() -> None:
    session = own_chrome_session(headless=True)
    driver = session.driver
    driver.quit()
    session.close()
    session.close()


def test_close_quits_injected_driver_and_blocks_reuse(server: LocalServer) -> None:
    driver = webdriver.Chrome(options=chrome_options(server, headless=True))
    session = requestium.Session(driver=driver)
    assert session.driver is driver
    session.close()
    assert driver_is_dead(driver)
    with pytest.raises(RuntimeError, match="closed"):
        session.driver  # noqa: B018


def test_injected_class_is_cached_across_sessions(server: LocalServer) -> None:
    drivers = [webdriver.Chrome(options=chrome_options(server, headless=True)) for _ in range(2)]
    try:
        sessions = [requestium.Session(driver=d) for d in drivers]
        assert type(drivers[0]) is type(drivers[1])
        assert DriverMixin in type(drivers[0]).__mro__
        assert sessions[0].driver is drivers[0]
    finally:
        for d in drivers:
            d.quit()


def test_injected_remote_class_has_mixin_in_mro() -> None:
    cls = _mixin_class(webdriver.Remote)
    assert cls.__mro__[1] is DriverMixin
    assert issubclass(cls, webdriver.Remote)
    assert "selector" in dir(cls)


@pytest.mark.parametrize("verb", ["get", "head", "post", "put", "patch", "delete", "options"])
def test_every_verb_is_wrapped_and_tracks_last_url(server: LocalServer, verb: str) -> None:
    session = requestium.Session()
    url = f"{server.url}/?verb={verb}"
    resp = getattr(session, verb)(url)
    assert isinstance(resp, RequestiumResponse)
    assert resp.status_code == 200
    assert session._last_requests_url == url
    assert server.requests()[-1] == (verb.upper(), f"127.0.0.1:{server.port}", f"/?verb={verb}")
    if verb != "head":
        assert resp.xpath("//h1/text()").get() == "Test Header 1"

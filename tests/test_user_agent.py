from collections.abc import Generator

import pytest

import requestium.requestium

from .conftest import LocalServer


@pytest.fixture
def reset_session_headers(session: requestium.Session) -> Generator[requestium.Session, None, None]:
    """Reset session headers before each test."""
    # Store original headers - convert to dict to copy
    original_headers = dict(session.headers)
    session.headers.clear()
    session.headers.update(original_headers)  # Restore to clean state at start

    yield session

    # Restore original headers after test
    session.headers.clear()
    session.headers.update(original_headers)


def test_copy_user_agent_from_driver(reset_session_headers: requestium.Session, server: LocalServer) -> None:
    """Ensure that requests sends the driver's user-agent after calling session.copy_user_agent_from_driver()."""
    session = reset_session_headers
    pre_copy_requests_useragent = str(session.headers["user-agent"])
    assert pre_copy_requests_useragent.startswith("python-requests/")
    assert session.get(f"{server.url}/echo").json()["headers"]["user-agent"] == pre_copy_requests_useragent

    session.driver.get(f"{server.url}/echo")
    driver_useragent = session.driver.execute_script("return navigator.userAgent;")
    session.copy_user_agent_from_driver()

    assert session.headers["user-agent"] == driver_useragent
    assert driver_useragent != pre_copy_requests_useragent
    assert session.get(f"{server.url}/echo").json()["headers"]["user-agent"] == driver_useragent


def test_transfer_driver_cookies_to_session_copies_user_agent(reset_session_headers: requestium.Session) -> None:
    session = reset_session_headers
    driver_useragent = session.driver.execute_script("return navigator.userAgent;")

    session.transfer_driver_cookies_to_session()
    assert session.headers["user-agent"] == driver_useragent


def test_transfer_driver_cookies_to_session_can_skip_user_agent(reset_session_headers: requestium.Session) -> None:
    session = reset_session_headers
    before = session.headers["user-agent"]

    session.transfer_driver_cookies_to_session(copy_user_agent=False)
    assert session.headers["user-agent"] == before

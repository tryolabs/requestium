from collections.abc import Generator

import pytest

import requestium.requestium


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


def test_copy_user_agent_from_driver(reset_session_headers: requestium.Session, example_html: str) -> None:
    """Ensure that requests user-agent header has been changed after calling session.copy_user_agent_from_driver()."""
    session = reset_session_headers
    pre_copy_requests_useragent = session.headers["user-agent"]
    assert pre_copy_requests_useragent
    assert pre_copy_requests_useragent != ""

    session.driver.get(f"data:text/html,{example_html}")
    session.copy_user_agent_from_driver()
    post_copy_requests_useragent = session.headers["user-agent"]

    assert post_copy_requests_useragent != pre_copy_requests_useragent

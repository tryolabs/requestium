import pytest
from _pytest.fixtures import FixtureRequest
from selenium.common import InvalidCookieDomainException

import requestium.requestium


@pytest.fixture(
    params=[
        {"name": "session_id", "value": "abc123", "domain": "example.com", "path": "/"},
        {"name": "user_token", "value": "xyz789", "domain": "example.com", "path": "/"},
    ],
    ids=["session_id", "user_token"],
    scope="module",
)
def cookie_data(request: FixtureRequest) -> dict[str, str]:
    return request.param


@pytest.fixture
def clean_session(session: requestium.Session) -> requestium.Session:
    """Fixture that ensures cookies are cleared before each test."""
    session.cookies.clear()
    session.driver.delete_all_cookies()
    return session


def test_transfer_driver_cookies_to_session(clean_session: requestium.Session, cookie_data: dict[str, str]) -> None:
    clean_session.driver.get(f"https://{cookie_data['domain']}")
    clean_session.driver.add_cookie(cookie_data)

    assert not clean_session.cookies.keys()
    clean_session.transfer_driver_cookies_to_session()
    assert clean_session.cookies.keys() == [cookie_data["name"]]


def test_transfer_session_cookies_to_driver(clean_session: requestium.Session, cookie_data: dict[str, str]) -> None:
    clean_session.get(f"http://{cookie_data['domain']}")
    clean_session.cookies.set(name=cookie_data["name"], value=cookie_data["value"], domain=cookie_data["domain"], path=cookie_data["path"])

    assert not clean_session.driver.get_cookies()
    clean_session.transfer_session_cookies_to_driver()

    driver_cookies = clean_session.driver.get_cookies()
    assert len(driver_cookies) == 1

    cookie = driver_cookies[0]
    assert cookie["name"] == cookie_data["name"]
    assert cookie["value"] == cookie_data["value"]
    assert cookie["domain"] in {cookie_data["domain"], f".{cookie_data['domain']}"}
    assert cookie["path"] == cookie_data["path"]


def test_transfer_session_cookies_to_driver_domain_filter(clean_session: requestium.Session, cookie_data: dict[str, str]) -> None:
    clean_session.get(f"http://{cookie_data['domain']}")
    clean_session.cookies.set(name="junk_cookie", value="sfkjn782", domain="google.com", path=cookie_data["path"])
    clean_session.cookies.set(name=cookie_data["name"], value=cookie_data["value"], domain=cookie_data["domain"], path=cookie_data["path"])

    assert not clean_session.driver.get_cookies()
    clean_session.transfer_session_cookies_to_driver(domain=cookie_data["domain"])

    driver_cookies = clean_session.driver.get_cookies()
    assert len(driver_cookies) == 1

    cookie = driver_cookies[0]
    assert cookie["name"] == cookie_data["name"]
    assert cookie["value"] == cookie_data["value"]
    assert cookie["domain"] in {cookie_data["domain"], f".{cookie_data['domain']}"}
    assert cookie["path"] == cookie_data["path"]


def test_transfer_session_cookies_to_driver_no_domain_error(session: requestium.Session) -> None:
    session.cookies.clear()
    session.driver.delete_all_cookies()
    session._last_requests_url = None

    with pytest.raises(
        InvalidCookieDomainException,
        match="Trying to transfer cookies to selenium without specifying a domain and without having visited any page in the current session",
    ):
        session.transfer_session_cookies_to_driver()

import pytest
from selenium.common import InvalidCookieDomainException

import requestium.requestium


@pytest.fixture(
    params=[
        {"name": "session_id", "value": "abc123", "domain": "example.com", "path": "/"},
        {"name": "user_token", "value": "xyz789", "domain": "example.com", "path": "/"},
    ],
    ids=["session_id", "user_token"],
)
def cookie_data(request) -> dict[str, str]:  # noqa: ANN001
    return request.param


def test_transfer_session_cookies_to_driver(session: requestium.Session, cookie_data: dict[str, str]) -> None:
    session.get(f"http://{cookie_data['domain']}")
    session.cookies.set(name=cookie_data["name"], value=cookie_data["value"], domain=cookie_data["domain"], path=cookie_data["path"])

    assert session.driver.get_cookies() == []
    session.transfer_session_cookies_to_driver()
    driver_cookies = session.driver.get_cookies()
    assert len(driver_cookies) == 1
    assert driver_cookies[0]["name"] == cookie_data["name"]
    assert driver_cookies[0]["value"] == cookie_data["value"]
    assert driver_cookies[0]["domain"] in [cookie_data["domain"], f".{cookie_data['domain']}"]
    assert driver_cookies[0]["path"] == cookie_data["path"]


def test_transfer_session_cookies_to_driver_no_domain_error(session: requestium.Session) -> None:
    with (
        pytest.raises(
            InvalidCookieDomainException,
            match="Trying to transfer cookies to selenium without specifying a domain and without having visited any page in the current session",
        ),
    ):
        session.transfer_session_cookies_to_driver()

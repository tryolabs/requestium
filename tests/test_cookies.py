import pytest
from selenium.common import InvalidCookieDomainException

import requestium


def test_transfer_session_cookies_to_driver(session: requestium.Session) -> None:
    assert session.cookies.keys() == []
    response = session.get("http://google.com/")
    assert response.cookies.keys().sort() == ["AEC", "NID"].sort()
    session.transfer_session_cookies_to_driver()
    assert session.cookies.keys() == ["AEC", "NID"]


def test_transfer_session_cookies_to_driver_no_domain_error(session: requestium.Session) -> None:
    with (
        pytest.raises(
            InvalidCookieDomainException,
            match="Trying to transfer cookies to selenium without specifying a domain and without having visited any page in the current session",
        ),
    ):
        session.transfer_session_cookies_to_driver()

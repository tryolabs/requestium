import pytest
from selenium.common import InvalidCookieDomainException

import requestium.requestium


def test_transfer_session_cookies_to_driver(session: requestium.Session) -> None:
    assert session.cookies.keys() == []
    response = session.get("http://google.com/")
    assert session.cookies.keys() != []
    session.transfer_session_cookies_to_driver()
    assert response.cookies.keys().sort() == session.cookies.keys().sort()


def test_transfer_session_cookies_to_driver_no_domain_error(session: requestium.Session) -> None:
    with (
        pytest.raises(
            InvalidCookieDomainException,
            match="Trying to transfer cookies to selenium without specifying a domain and without having visited any page in the current session",
        ),
    ):
        session.transfer_session_cookies_to_driver()

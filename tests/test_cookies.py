import pytest
from selenium.common import InvalidCookieDomainException

import requestium
from test_session import session_parameters


@pytest.mark.parametrize("params", session_parameters)
def test_transfer_session_cookies_to_driver_no_domain_error(params) -> None:
    with (
        requestium.Session(**params) as session,
        pytest.raises(
            InvalidCookieDomainException,
            match="Trying to transfer cookies to selenium without specifying a domain and without having visited any page in the current session",
        ),
    ):
        session.transfer_session_cookies_to_driver()

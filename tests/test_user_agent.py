import pytest

import requestium
from test_session import session_parameters


@pytest.mark.parametrize("params", session_parameters)
def test_copy_user_agent_from_driver(params) -> None:
    """Ensure that requests user-agent header has been changed after calling session.copy_user_agent_from_driver()"""
    with requestium.Session(**params) as session:
        pre_copy_requests_useragent = session.headers["user-agent"]
        assert pre_copy_requests_useragent and pre_copy_requests_useragent != ""

        session.driver.get("http://the-internet.herokuapp.com")
        session.copy_user_agent_from_driver()
        post_copy_requests_useragent = session.headers["user-agent"]

        assert post_copy_requests_useragent != pre_copy_requests_useragent

import requestium.requestium


def test_copy_user_agent_from_driver(session: requestium.Session, example_html: str) -> None:
    """Ensure that requests user-agent header has been changed after calling session.copy_user_agent_from_driver()."""
    pre_copy_requests_useragent = session.headers["user-agent"]
    assert pre_copy_requests_useragent
    assert pre_copy_requests_useragent != ""

    session.driver.get(f"data:text/html,{example_html}")
    session.copy_user_agent_from_driver()
    post_copy_requests_useragent = session.headers["user-agent"]

    assert post_copy_requests_useragent != pre_copy_requests_useragent

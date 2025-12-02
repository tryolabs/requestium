import pytest

import requestium.requestium


def test__start_chrome_driver(session: requestium.Session, example_html: str) -> None:
    session._start_chrome_browser()
    session.driver.get(f"data:text/html,{example_html}")
    title = session.driver.title
    assert title == "The Internet"


def test__start_chrome_driver_options_typeerror() -> None:
    invalid_webdriver_options = {"arguments": "invalid_string"}
    with (
        requestium.Session(webdriver_options=invalid_webdriver_options) as session,
        pytest.raises(
            TypeError,
            match=f"'arguments' option must be a list, but got {type(invalid_webdriver_options['arguments']).__name__}",
        ),
    ):
        session._start_chrome_browser()

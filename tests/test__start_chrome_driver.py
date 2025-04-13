import time

import pytest

import requestium


def test__start_chrome_driver() -> None:
    with requestium.Session() as session:
        session._start_chrome_browser()
        session.driver.get("http://the-internet.herokuapp.com")
        time.sleep(1)
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

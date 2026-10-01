"""How session.proxies is turned into Chrome's --proxy-server argument."""

import warnings

import pytest

import requestium

from .conftest import DISABLE_HTTPS_UPGRADES, LocalServer

PROXIED_HOST = "requestium-proxy-test.invalid"


def test_proxy_flag_reaches_chrome(server: LocalServer) -> None:
    session = requestium.Session(headless=True, webdriver_options={"arguments": [DISABLE_HTTPS_UPGRADES]})
    try:
        # Set after construction but before the first driver access
        session.proxies = {"http": server.url}
        session.driver.get(f"http://{PROXIED_HOST}/page")
        assert ("GET", PROXIED_HOST, "/page") in server.requests()
    finally:
        session.close()


def test_proxy_flag_skipped_when_user_supplied() -> None:
    session = requestium.Session(webdriver_options={"arguments": ["--proxy-server=http://user.example:1"]})
    session.proxies = {"http": "http://session.example:2", "https": "http://session.example:3"}
    assert session._session_chrome_arguments(["--proxy-server=http://user.example:1"]) == []


def test_proxy_flag_format() -> None:
    session = requestium.Session()
    session.proxies = {"http": "http://a.example:1", "https": "socks5://b.example:2"}
    assert session._session_chrome_arguments([]) == ["--proxy-server=http=a.example:1;https=socks5://b.example:2"]


def test_credentialed_proxy_warns_and_is_skipped() -> None:
    session = requestium.Session(headless=True)
    session.proxies = {"http": "http://user:secret@proxy.example:8080"}
    try:
        with pytest.warns(UserWarning, match="credentials") as record:
            session.driver.get("data:text/html,<p>ok</p>")
        assert record[0].filename == __file__
    finally:
        session.close()


def test_no_warnings_without_credentials() -> None:
    session = requestium.Session(headless=True)
    session.proxies = {"http": "http://proxy.example:8080"}
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert session._session_chrome_arguments([]) == ["--proxy-server=http=proxy.example:8080"]

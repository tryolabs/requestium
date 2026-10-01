from __future__ import annotations

import threading
import time
import warnings
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING

import pytest
from selenium import webdriver

import requestium
from requestium.requestium import DriverMixin, RequestiumResponse, Session
from requestium.requestium_session import _mixin_class

if TYPE_CHECKING:
    from collections.abc import Iterator

    from selenium.webdriver.remote.webdriver import WebDriver

PROXIED_HOST = "requestium-proxy-test.invalid"


class Handler(BaseHTTPRequestHandler):
    """Answers every verb with 200 and records '<method> <request target>' in the server's 'requests' list."""

    def _respond(self) -> None:
        self.server.requests.append(f"{self.command} {self.path}")  # type: ignore[attr-defined]
        body = b"<html><body><p id='x'>hello</p></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", "0" if self.command == "HEAD" else str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _respond  # noqa: N815

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


@pytest.fixture
def server() -> Iterator[ThreadingHTTPServer]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.requests = []  # type: ignore[attr-defined]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()


def base_url(httpd: ThreadingHTTPServer) -> str:
    return f"http://127.0.0.1:{httpd.server_address[1]}"


def chrome_options() -> webdriver.ChromeOptions:
    options = webdriver.ChromeOptions()
    options.add_argument("headless=new")
    return options


def localhost_options(httpd: ThreadingHTTPServer) -> dict[str, list[str]]:
    """Make http://localhost:<port> reach the test server (it may otherwise resolve to ::1) and count as a secure context for Secure cookies."""
    return {
        "arguments": ["--host-resolver-rules=MAP localhost 127.0.0.1", f"--unsafely-treat-insecure-origin-as-secure=http://localhost:{httpd.server_address[1]}"]
    }


def driver_is_dead(driver: WebDriver) -> bool:
    return not driver.service.is_connectable()  # type: ignore[attr-defined]


def test_close_quits_lazily_started_chrome() -> None:
    session = Session(headless=True)
    driver = session.driver
    assert not driver_is_dead(driver)
    session.close()
    assert driver_is_dead(driver)
    assert session._driver is None


def test_close_then_driver_access_starts_fresh_chrome() -> None:
    session = Session(headless=True)
    first = session.driver
    session.close()
    second = session.driver
    try:
        assert second is not first
        assert second.execute_script("return 1 + 1;") == 2
    finally:
        session.close()


def test_context_manager_quits_driver() -> None:
    with Session(headless=True) as session:
        driver = session.driver
        assert not driver_is_dead(driver)
    assert driver_is_dead(driver)


def test_close_without_driver_does_not_start_one() -> None:
    session = Session(headless=True)
    session.close()
    assert session._driver is None


def test_close_twice_is_harmless() -> None:
    session = Session(headless=True)
    driver = session.driver
    driver.quit()
    session.close()
    session.close()


def test_close_quits_injected_driver_and_blocks_reuse() -> None:
    driver = webdriver.Chrome(options=chrome_options())
    session = Session(driver=driver)
    assert session.driver is driver
    session.close()
    assert driver_is_dead(driver)
    with pytest.raises(RuntimeError, match="closed"):
        session.driver  # noqa: B018


def test_injected_chrome_gets_helpers() -> None:
    driver = webdriver.Chrome(options=chrome_options())
    try:
        session = Session(driver=driver, default_timeout=3)
        assert session.driver.default_timeout == 3  # type: ignore[attr-defined]
        session.driver.get("data:text/html,<p class='a'>hello 42</p><p class='a'>bye</p>")
        assert session.driver.xpath("//p/text()").getall() == ["hello 42", "bye"]
        assert session.driver.css("p.a::text").get() == "hello 42"
        assert session.driver.re(r"\d+") == ["42"]
        assert session.driver.re_first(r"hello (\d+)") == "42"
        assert isinstance(session.driver, webdriver.Chrome)
    finally:
        driver.quit()


def test_injected_class_is_cached_across_sessions() -> None:
    drivers = [webdriver.Chrome(options=chrome_options()) for _ in range(2)]
    try:
        sessions = [Session(driver=d) for d in drivers]
        assert type(drivers[0]) is type(drivers[1])
        assert DriverMixin in type(drivers[0]).__mro__
        assert sessions[0].driver is drivers[0]
    finally:
        for d in drivers:
            d.quit()


def test_injected_firefox_gets_helpers() -> None:
    options = webdriver.FirefoxOptions()
    options.add_argument("-headless")
    try:
        driver = webdriver.Firefox(options=options)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Firefox unavailable: {e}")
    try:
        session = Session(driver=driver)
        session.driver.get("data:text/html,<p>hello 42</p>")
        assert session.driver.xpath("//p/text()").get() == "hello 42"
        assert session.driver.css("p::text").get() == "hello 42"
        assert session.driver.re_first(r"\d+") == "42"
    finally:
        driver.quit()


def test_injected_remote_class_has_mixin_in_mro() -> None:
    cls = _mixin_class(webdriver.Remote)
    assert cls.__mro__[1] is DriverMixin
    assert issubclass(cls, webdriver.Remote)
    assert "selector" in dir(cls)


@pytest.mark.parametrize("verb", ["get", "head", "post", "put", "patch", "delete", "options"])
def test_every_verb_is_wrapped_and_tracks_last_url(server: ThreadingHTTPServer, verb: str) -> None:
    session = Session()
    url = f"{base_url(server)}/{verb}"
    resp = getattr(session, verb)(url)
    assert isinstance(resp, RequestiumResponse)
    assert resp.status_code == 200
    assert session._last_requests_url == url
    assert server.requests == [f"{verb.upper()} /{verb}"]  # type: ignore[attr-defined]
    if verb != "head":
        assert resp.xpath("//p/text()").get() == "hello"


def test_proxy_flag_reaches_chrome() -> None:
    proxy = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    proxy.requests = []  # type: ignore[attr-defined]
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    session = Session(headless=True)
    try:
        # Set after construction but before the first driver access
        session.proxies = {"http": base_url(proxy)}
        session.driver.get(f"http://{PROXIED_HOST}/page")
        assert f"GET http://{PROXIED_HOST}/page" in proxy.requests  # type: ignore[attr-defined]
    finally:
        session.close()
        proxy.shutdown()
        proxy.server_close()


def test_proxy_flag_skipped_when_user_supplied() -> None:
    session = Session(webdriver_options={"arguments": ["--proxy-server=http://user.example:1"]})
    session.proxies = {"http": "http://session.example:2", "https": "http://session.example:3"}
    assert session._session_chrome_arguments(["--proxy-server=http://user.example:1"]) == []


def test_proxy_flag_format() -> None:
    session = Session()
    session.proxies = {"http": "http://a.example:1", "https": "socks5://b.example:2"}
    assert session._session_chrome_arguments([]) == ["--proxy-server=http=a.example:1;https=socks5://b.example:2"]


def test_credentialed_proxy_warns_and_is_skipped() -> None:
    session = Session(headless=True)
    session.proxies = {"http": "http://user:secret@proxy.example:8080"}
    try:
        with pytest.warns(UserWarning, match="credentials") as record:
            session.driver.get("data:text/html,<p>ok</p>")
        assert record[0].filename == __file__
    finally:
        session.close()


def test_custom_user_agent_reaches_chrome() -> None:
    session = Session(headless=True)
    session.headers["User-Agent"] = "RequestiumTest/1.0"
    try:
        assert session.driver.execute_script("return navigator.userAgent;") == "RequestiumTest/1.0"
    finally:
        session.close()


def test_default_user_agent_is_not_forced() -> None:
    session = Session(headless=True)
    try:
        assert "RequestiumTest" not in session.driver.execute_script("return navigator.userAgent;")
        assert "python-requests" not in session.driver.execute_script("return navigator.userAgent;")
    finally:
        session.close()


def test_user_supplied_user_agent_argument_wins() -> None:
    session = Session(headless=True, webdriver_options={"arguments": ["--user-agent=FromOptions/2.0"]})
    session.headers["User-Agent"] = "FromHeaders/1.0"
    try:
        assert session.driver.execute_script("return navigator.userAgent;") == "FromOptions/2.0"
    finally:
        session.close()


def test_session_cookie_secure_and_path_reach_driver(server: ThreadingHTTPServer) -> None:
    session = Session(headless=True, webdriver_options=localhost_options(server))
    session.cookies.set("sec", "1", domain="localhost", path="/sub", secure=True)
    session.cookies.set("plain", "2", domain="localhost", path="/")
    try:
        # Already being on the cookie's domain (and path) keeps the transfer from navigating to its default port
        session.driver.get(base_url(server).replace("127.0.0.1", "localhost") + "/sub")
        session.transfer_session_cookies_to_driver(domain="localhost")
        cookies = {c["name"]: c for c in session.driver.get_cookies()}
        assert cookies["sec"]["secure"] is True
        assert cookies["sec"]["path"] == "/sub"
        assert cookies["plain"]["secure"] is False
        assert cookies["plain"]["path"] == "/"
    finally:
        session.close()


def test_driver_cookie_path_secure_expiry_reach_session(server: ThreadingHTTPServer) -> None:
    session = Session(headless=True, webdriver_options=localhost_options(server))
    try:
        session.driver.get(base_url(server).replace("127.0.0.1", "localhost") + "/deep")
        expiry = int(time.time()) + 3600
        session.driver.add_cookie({"name": "c", "value": "v", "path": "/deep", "secure": True, "expiry": expiry})
        session.transfer_driver_cookies_to_session(copy_user_agent=False)
        cookie = next(c for c in session.cookies if c.name == "c")
        assert cookie.path == "/deep"
        assert cookie.secure is True
        assert cookie.expires == expiry
    finally:
        session.close()


def test_public_api_exports_session() -> None:
    assert requestium.Session is Session


def test_no_warnings_without_credentials() -> None:
    session = Session(headless=True)
    session.proxies = {"http": "http://proxy.example:8080"}
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert session._session_chrome_arguments([]) == ["--proxy-server=http=proxy.example:8080"]

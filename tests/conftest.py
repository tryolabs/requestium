import contextlib
import json
import threading
from collections.abc import Generator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, cast
from urllib.parse import parse_qs, urlsplit

import pytest
import urllib3.exceptions
from _pytest.fixtures import FixtureRequest
from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.wait import WebDriverWait

import requestium

if TYPE_CHECKING:
    from requestium.requestium_mixin import DriverMixin


EXAMPLE_HTML = """
<html>
    <head><title>The Internet</title></head>
    <body>
        <h1>Test Header 1</h1>
        <h2 id="test-header">Test Header 2</h2>
        <h3 class="test-header-3">Test Header 3</h3>
        <p class="body-text">Test Paragraph 1</p>
        <button>Click Me</button>
        <p><a href="example.com" name="link-paragraph">Test Link 1</a></p>
        <p><a href="example.com">Test Link 2</a></p>
    </body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    """
    Serves pages and small JSON endpoints, and doubles as an HTTP forward proxy.

    Browsers and requests can be pointed at this server as their proxy (see LocalServer.proxy_url), which lets
    tests use realistic multi-label hostnames like example.com without touching the network. Proxied requests
    arrive with an absolute URL in the request line, so only its path is used for routing.

    Routes:
        /                     the example page (redirects www.<host> to <host>, like many real sites do)
        /echo                 JSON with the request method, headers, cookies and body
        /set-cookie           sets a cookie from the query string: name, value and optionally domain
        /redirect             302 to /
        anything added with LocalServer.add_page
    """

    server: "_Server"

    def _send(self, status: int, body: str, content_type: str = "text/html", headers: dict[str, str] | None = None) -> None:
        payload = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def _handle(self) -> None:
        url = urlsplit(self.path)
        query = {key: values[0] for key, values in parse_qs(url.query).items()}
        host = self.headers.get("Host", "")
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode() if length else ""

        if url.path == "/" and host.startswith("www."):
            self._send(302, "", headers={"Location": f"http://{host.removeprefix('www.')}/"})
        elif url.path == "/redirect":
            self._send(302, "", headers={"Location": "/"})
        elif url.path == "/set-cookie":
            cookie = f"{query['name']}={query['value']}; Path=/"
            if "domain" in query:
                cookie += f"; Domain={query['domain']}"
            self._send(200, EXAMPLE_HTML, headers={"Set-Cookie": cookie})
        elif url.path == "/echo":
            echo = {
                "method": self.command,
                "headers": {name.lower(): value for name, value in self.headers.items()},
                "cookies": self.headers.get("Cookie", ""),
                "body": body,
            }
            self._send(200, json.dumps(echo), content_type="application/json")
        elif url.path == "/":
            self._send(200, EXAMPLE_HTML)
        elif url.path in self.server.pages:
            self._send(200, self.server.pages[url.path])
        else:
            self._send(404, "not found")

    do_GET = do_POST = do_PUT = _handle  # noqa: N815

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        """Keep test output quiet."""


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.pages: dict[str, str] = {}


class LocalServer:
    """A real HTTP server on 127.0.0.1 running in a background thread."""

    def __init__(self) -> None:
        self._server = _Server()
        self.port: int = self._server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        # Lets requests reach fake public hostnames (http only) through this server
        self.proxy_url = self.url
        self.proxies = {"http": self.proxy_url}
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def add_page(self, path: str, html: str) -> str:
        """Serve html at path (leading slash) and return its full URL."""
        self._server.pages[path] = html
        return f"{self.url}{path}"

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


@pytest.fixture(scope="session")
def server() -> Generator[LocalServer, None, None]:
    """One server per pytest process, so one per xdist worker."""
    local_server = LocalServer()
    yield local_server
    local_server.close()


@pytest.fixture(scope="module")
def example_html() -> str:
    return EXAMPLE_HTML


@pytest.fixture
def example_url(server: LocalServer) -> str:
    return server.add_page("/example", EXAMPLE_HTML)


def chrome_options(server: LocalServer, *, headless: bool) -> webdriver.ChromeOptions:
    """Chrome options that route non-loopback http traffic (e.g. http://example.com) to the local server."""
    options = webdriver.ChromeOptions()
    options.add_argument(f"--proxy-server={server.proxy_url}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if headless:
        options.add_argument("--headless=new")
    return options


def _create_chrome_driver(server: LocalServer, *, headless: bool) -> webdriver.Chrome:
    try:
        driver = webdriver.Chrome(options=chrome_options(server, headless=headless))
        WebDriverWait(driver, 5).until(EC.number_of_windows_to_be(1))
        return driver
    except (urllib3.exceptions.ReadTimeoutError, TimeoutError, WebDriverException) as e:
        error_msg = f"Chrome driver initialization failed: {e}"
        raise RuntimeError(error_msg) from e


def _create_firefox_driver(server: LocalServer, *, headless: bool) -> webdriver.Firefox:
    options = webdriver.FirefoxOptions()
    options.set_preference("network.proxy.type", 1)
    options.set_preference("network.proxy.http", "127.0.0.1")
    options.set_preference("network.proxy.http_port", server.port)
    options.set_preference("browser.cache.disk.enable", value=False)
    options.set_preference("browser.cache.memory.enable", value=False)
    options.set_preference("browser.cache.offline.enable", value=False)
    options.set_preference("network.http.use-cache", value=False)
    if headless:
        options.add_argument("--headless")

    try:
        driver = webdriver.Firefox(options=options)
        WebDriverWait(driver, 5).until(EC.number_of_windows_to_be(1))
        return driver
    except (urllib3.exceptions.ReadTimeoutError, TimeoutError, WebDriverException) as e:
        error_msg = f"Firefox driver initialization failed: {e}"
        raise RuntimeError(error_msg) from e


def validate_session(session: requestium.Session) -> None:
    """
    Check basic validity of requestium Session object.

    If browser context is missing, try recovering.
    If attempted recovery raises WebDriverException, skip test.
    """
    try:
        _ = session.driver.current_url
        _ = session.driver.window_handles
    except WebDriverException as e:
        if "Browsing context has been discarded" not in str(e):
            raise

        try:
            session.driver.switch_to.new_window("tab")
        except WebDriverException as e:
            pytest.skip(f"Browser context discarded and cannot be recovered: {e!s}")


@pytest.fixture(
    params=["chrome-headless", "chrome", "firefox-headless", "firefox"],
    scope="module",
)
def session(request: FixtureRequest, server: LocalServer) -> Generator[requestium.Session, None, None]:
    driver_type = request.param
    browser, _, mode = driver_type.partition("-")
    headless = mode == "headless"

    driver: webdriver.Chrome | webdriver.Firefox | None = None

    try:
        if browser == "chrome":
            driver = _create_chrome_driver(server, headless=headless)
        elif browser == "firefox":
            driver = _create_firefox_driver(server, headless=headless)
        else:
            msg = f"Unknown driver type: {browser}"
            raise ValueError(msg)

        assert driver.name in browser
        session = requestium.Session(driver=cast("DriverMixin", driver))
        assert session.driver.name in browser

        validate_session(session)

        yield session

    except RuntimeError as e:
        # Driver creation failed - skip all tests using this session
        pytest.skip(str(e))

    finally:
        if driver:
            with contextlib.suppress(WebDriverException, OSError, Exception):
                driver.quit()

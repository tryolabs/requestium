"""
Cookie and timeout edge cases, run against a real headless Chrome and local HTTP/HTTPS servers.

Chrome maps the fake hostnames below to the local servers through --host-resolver-rules (which also
rewrites the port), so ensure_add_cookie can navigate to "http://www.example.com" with no network access.
"""

import copy
import http.server
import shutil
import ssl
import subprocess
import threading
from collections.abc import Generator
from pathlib import Path

import pytest
from selenium.common.exceptions import NoSuchWindowException, TimeoutException, WebDriverException

import requestium
from requestium.requestium_mixin import DriverMixin

PAGE = b"<html><body><p id='x'>hi</p></body></html>"


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        host = self.headers.get("Host", "")
        self.server.requests.append((self.server.scheme, host, self.path))  # type: ignore[attr-defined]
        if host.startswith("www.redirect.com"):
            self.send_response(302)
            self.send_header("Location", "http://app.redirect.com/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(PAGE)))
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *args: object) -> None:
        pass


def _serve(scheme: str, certfile: Path | None = None) -> http.server.ThreadingHTTPServer:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.scheme = scheme  # type: ignore[attr-defined]
    server.requests = []  # type: ignore[attr-defined]
    if certfile:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture(scope="module")
def servers(tmp_path_factory: pytest.TempPathFactory) -> Generator[tuple[http.server.ThreadingHTTPServer, http.server.ThreadingHTTPServer]]:
    if shutil.which("openssl") is None:
        pytest.skip("openssl is needed to generate a throwaway TLS certificate")
    pem = tmp_path_factory.mktemp("tls") / "cert.pem"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=localhost", "-keyout", str(pem), "-out", str(pem)],
        check=True,
        capture_output=True,
    )
    http_server, https_server = _serve("http"), _serve("https", pem)
    yield http_server, https_server
    http_server.shutdown()
    https_server.shutdown()


@pytest.fixture(scope="module")
def driver(servers: tuple[http.server.ThreadingHTTPServer, http.server.ThreadingHTTPServer]) -> Generator[DriverMixin]:
    http_port, https_port = (s.server_address[1] for s in servers)
    rules = ", ".join(
        [
            f"MAP *.example.com 127.0.0.1:{http_port}",
            f"MAP ample.com 127.0.0.1:{http_port}",
            f"MAP *.redirect.com 127.0.0.1:{http_port}",
            f"MAP *.secure.com 127.0.0.1:{https_port}",
        ],
    )
    options = {"arguments": ["--no-sandbox", "--disable-dev-shm-usage", f"--host-resolver-rules={rules}", "--ignore-certificate-errors"]}
    session = requestium.Session(headless=True, webdriver_options=options)
    try:
        yield session.driver
    finally:
        session.driver.quit()


def _requests(server: http.server.ThreadingHTTPServer) -> list[tuple[str, str, str]]:
    return [r for r in server.requests if r[2] != "/favicon.ico"]  # type: ignore[attr-defined]


def test_ensure_add_cookie_does_not_mutate_input(driver: DriverMixin) -> None:
    cookie = {"name": "a", "value": "1", "domain": "www.example.com"}
    original = copy.deepcopy(cookie)
    driver.ensure_add_cookie(cookie, override_domain="example.com")
    assert cookie == original
    assert any(c["name"] == "a" and c["domain"] in ("example.com", ".example.com") for c in driver.get_cookies())


def test_retry_with_permissive_domain(driver: DriverMixin) -> None:
    # www.redirect.com redirects to app.redirect.com, so a cookie for www.redirect.com is rejected there
    # and only succeeds on retry with the registrable domain.
    cookie = {"name": "retry", "value": "1", "domain": "www.redirect.com"}
    driver.ensure_add_cookie(cookie)
    assert driver.current_url.startswith("http://app.redirect.com")
    assert cookie["domain"] == "www.redirect.com"
    assert any(c["name"] == "retry" and c["domain"].lstrip(".") == "redirect.com" for c in driver.get_cookies())


def test_non_domain_errors_propagate_with_message(driver: DriverMixin) -> None:
    main = driver.current_window_handle
    driver.switch_to.new_window("tab")
    driver.close()
    try:
        # The current window no longer exists: not a domain problem, so the original exception must surface.
        with pytest.raises(NoSuchWindowException) as excinfo:
            driver.try_add_cookie({"name": "bad", "value": "1", "domain": "www.example.com"})
        assert "no such window" in str(excinfo.value)
    finally:
        driver.switch_to.window(main)


def test_unfixable_cookie_raises_after_retry(driver: DriverMixin) -> None:
    driver.get("http://www.example.com/")
    # Browsers silently drop a __Secure- cookie that isn't marked secure, which is the "silent no-op" case.
    with pytest.raises(WebDriverException, match="Couldn't add the following cookie"):
        driver.ensure_add_cookie({"name": "__Secure-nope", "value": "1", "domain": "www.example.com"})


def test_secure_cookie_navigates_over_https(
    driver: DriverMixin,
    servers: tuple[http.server.ThreadingHTTPServer, http.server.ThreadingHTTPServer],
) -> None:
    http_server, https_server = servers
    driver.ensure_add_cookie({"name": "sec", "value": "1", "domain": "www.secure.com", "secure": True})
    assert driver.current_url.startswith("https://www.secure.com")
    assert ("https", "www.secure.com", "/") in _requests(https_server)
    assert not any(host.startswith("www.secure.com") for _, host, _ in _requests(http_server))


def test_insecure_cookie_navigates_over_http(
    driver: DriverMixin,
    servers: tuple[http.server.ThreadingHTTPServer, http.server.ThreadingHTTPServer],
) -> None:
    http_server, _ = servers
    driver.ensure_add_cookie({"name": "plain", "value": "1", "domain": "www.plain.example.com"})
    assert driver.current_url.startswith("http://www.plain.example.com")
    assert ("http", "www.plain.example.com", "/") in _requests(http_server)


def test_domain_check_is_not_a_substring_match(
    driver: DriverMixin,
    servers: tuple[http.server.ThreadingHTTPServer, http.server.ThreadingHTTPServer],
) -> None:
    http_server, _ = servers
    driver.get("http://www.example.com/")
    # "ample.com" is a substring of "www.example.com" but not a parent domain, so we must navigate there.
    driver.ensure_add_cookie({"name": "sub", "value": "1", "domain": "ample.com"})
    assert ("http", "ample.com", "/") in _requests(http_server)
    assert driver.current_url.startswith("http://ample.com")


def test_parent_domain_cookie_does_not_navigate(
    driver: DriverMixin,
    servers: tuple[http.server.ThreadingHTTPServer, http.server.ThreadingHTTPServer],
) -> None:
    http_server, _ = servers
    driver.get("http://www.example.com/")
    before = len(_requests(http_server))
    driver.ensure_add_cookie({"name": "parent", "value": "1", "domain": ".example.com"})
    assert len(_requests(http_server)) == before
    assert driver.current_url.startswith("http://www.example.com")


def test_timeout_zero_is_honored(driver: DriverMixin) -> None:
    driver.default_timeout = 30
    driver.get("data:text/html,<p>hi</p>")
    with pytest.raises(TimeoutException):
        driver.ensure_element_by_id("missing", timeout=0)

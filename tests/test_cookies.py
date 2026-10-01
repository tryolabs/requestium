import time
from collections.abc import Generator

import pytest
from selenium.common import InvalidCookieDomainException

import requestium.requestium

from .conftest import LocalServer, assert_first_cookie_matches, cookies_sent_by_driver

# Cookie domains in these tests are fake public hostnames such as example.com. The browsers and requests are pointed at
# the local server as an HTTP proxy (see LocalServer), so nothing leaves the machine, yet cookie and domain rules are
# the real ones. Using the server directly at 127.0.0.1 doesn't work for the requestium cookie helpers, and browsers
# are picky about it:
#   - tldextract reports no registrable domain for IPs and "localhost", so ensure_add_cookie and
#     transfer_session_cookies_to_driver would navigate to http://127.0.0.1 (port 80) or give up on the domain
#   - a cookie with domain=localhost is rejected on an IP host (and vice versa) by both Chrome and Firefox
#   - Chrome and Firefox both accept domain=127.0.0.1 or no domain at all for a page on 127.0.0.1
# Plain http is required, as an https page would need a CONNECT tunnel to the proxy.


def echoed_cookies(session: requestium.Session, host: str) -> str:
    """Return the Cookie header the server received when the session fetched the host."""
    return session.get(f"http://{host}/echo").json()["cookies"]


def test_transfer_driver_cookies_to_session(clean_session: requestium.Session, cookie_data: dict[str, str]) -> None:
    clean_session.driver.get(f"http://{cookie_data['domain']}")
    clean_session.driver.add_cookie(cookie_data)

    assert not clean_session.cookies.keys()
    clean_session.transfer_driver_cookies_to_session()
    assert clean_session.cookies.keys() == [cookie_data["name"]]
    assert {cookie.name: cookie.value for cookie in clean_session.cookies} == {cookie_data["name"]: cookie_data["value"]}


def test_transfer_driver_cookies_to_session_reaches_server(clean_session: requestium.Session, cookie_data: dict[str, str]) -> None:
    """A cookie set by a server response in the browser is sent by requests after the transfer."""
    clean_session.driver.get(f"http://example.com/set-cookie?name={cookie_data['name']}&value={cookie_data['value']}")
    assert not echoed_cookies(clean_session, "example.com")

    clean_session.transfer_driver_cookies_to_session()

    assert echoed_cookies(clean_session, "example.com") == f"{cookie_data['name']}={cookie_data['value']}"


def test_transfer_driver_cookies_to_session_from_loopback_ip(clean_session: requestium.Session, server: LocalServer) -> None:
    """Driver to session works for IP hosts, because it doesn't need to work out a registrable domain."""
    clean_session.driver.get(server.url)
    clean_session.driver.delete_all_cookies()
    clean_session.driver.get(f"{server.url}/set-cookie?name=loopback&value=1")

    clean_session.transfer_driver_cookies_to_session()

    assert clean_session.get(f"{server.url}/echo").json()["cookies"] == "loopback=1"


def test_transfer_session_cookies_to_driver(clean_session: requestium.Session, cookie_data: dict[str, str]) -> None:
    clean_session.get(f"http://{cookie_data['domain']}")
    clean_session.cookies.set(name=cookie_data["name"], value=cookie_data["value"], domain=cookie_data["domain"], path=cookie_data["path"])

    assert not clean_session.driver.get_cookies()
    clean_session.transfer_session_cookies_to_driver()
    assert_first_cookie_matches(clean_session.driver.get_cookies(), cookie_data)


def test_transfer_session_cookies_to_driver_reaches_server(clean_session: requestium.Session, cookie_data: dict[str, str]) -> None:
    """A cookie set by a server response to requests is sent by the browser after the transfer."""
    clean_session.get(f"http://example.com/set-cookie?name={cookie_data['name']}&value={cookie_data['value']}")
    assert clean_session.cookies.keys() == [cookie_data["name"]]

    clean_session.transfer_session_cookies_to_driver()

    sent = cookies_sent_by_driver(clean_session)
    assert sent == f"{cookie_data['name']}={cookie_data['value']}"


def test_transfer_session_cookies_to_driver_domain_filter(clean_session: requestium.Session, cookie_data: dict[str, str]) -> None:
    clean_session.get(f"http://{cookie_data['domain']}")
    clean_session.cookies.set(name="junk_cookie", value="sfkjn782", domain="google.com", path=cookie_data["path"])
    clean_session.cookies.set(name=cookie_data["name"], value=cookie_data["value"], domain=cookie_data["domain"], path=cookie_data["path"])

    assert not clean_session.driver.get_cookies()
    clean_session.transfer_session_cookies_to_driver(domain=cookie_data["domain"])
    assert_first_cookie_matches(clean_session.driver.get_cookies(), cookie_data)


def test_transfer_session_cookies_to_driver_defaults_to_last_requested_domain(clean_session: requestium.Session) -> None:
    clean_session.cookies.set(name="other", value="1", domain="example.net", path="/")
    clean_session.cookies.set(name="wanted", value="2", domain="example.com", path="/")

    clean_session.get("http://example.com")
    clean_session.transfer_session_cookies_to_driver()

    assert_first_cookie_matches(clean_session.driver.get_cookies(), {"name": "wanted", "value": "2", "domain": "example.com", "path": "/"})


def test_transfer_session_cookies_to_driver_no_domain_error(clean_session: requestium.Session) -> None:
    with pytest.raises(
        InvalidCookieDomainException,
        match="Trying to transfer cookies to selenium without specifying a domain and without having visited any page in the current session",
    ):
        clean_session.transfer_session_cookies_to_driver()


@pytest.fixture(scope="module")
def localhost_session(server: LocalServer) -> Generator[requestium.Session, None, None]:
    """Start a Chrome session where http://localhost:<port> reaches the test server and counts as a secure context for Secure cookies."""
    arguments = ["--host-resolver-rules=MAP localhost 127.0.0.1", f"--unsafely-treat-insecure-origin-as-secure=http://localhost:{server.port}"]
    session = requestium.Session(headless=True, webdriver_options={"arguments": ["--no-sandbox", "--disable-dev-shm-usage", *arguments]})
    yield session
    session.close()


def test_secure_and_path_attributes_reach_driver(localhost_session: requestium.Session, server: LocalServer) -> None:
    session = localhost_session
    session.cookies.clear()
    session.cookies.set("sec", "1", domain="localhost", path="/sub", secure=True)
    session.cookies.set("plain", "2", domain="localhost", path="/")

    # Already being on the cookie's domain (and path) keeps the transfer from navigating to its default port
    session.driver.get(f"http://localhost:{server.port}/sub")
    session.transfer_session_cookies_to_driver(domain="localhost")

    cookies = {c["name"]: c for c in session.driver.get_cookies()}
    assert cookies["sec"]["secure"] is True
    assert cookies["sec"]["path"] == "/sub"
    assert cookies["plain"]["secure"] is False
    assert cookies["plain"]["path"] == "/"


def test_path_secure_and_expiry_reach_session(localhost_session: requestium.Session, server: LocalServer) -> None:
    session = localhost_session
    session.cookies.clear()
    session.driver.get(f"http://localhost:{server.port}/deep")
    expiry = int(time.time()) + 3600

    session.driver.add_cookie({"name": "c", "value": "v", "path": "/deep", "secure": True, "expiry": expiry})
    session.transfer_driver_cookies_to_session(copy_user_agent=False)

    cookie = next(c for c in session.cookies if c.name == "c")
    assert cookie.path == "/deep"
    assert cookie.secure is True
    assert cookie.expires == expiry

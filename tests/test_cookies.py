from collections.abc import Generator

import pytest
from _pytest.fixtures import FixtureRequest
from selenium.common import InvalidCookieDomainException

import requestium.requestium

from .conftest import LocalServer

# Cookie domains in these tests are fake public hostnames such as example.com. The browsers and requests are pointed at
# the local server as an HTTP proxy (see LocalServer), so nothing leaves the machine, yet cookie and domain rules are
# the real ones. Using the server directly at 127.0.0.1 doesn't work for the requestium cookie helpers, and browsers
# are picky about it:
#   - tldextract reports no registrable domain for IPs and "localhost", so ensure_add_cookie and
#     transfer_session_cookies_to_driver would navigate to http://127.0.0.1 (port 80) or give up on the domain
#   - a cookie with domain=localhost is rejected on an IP host (and vice versa) by both Chrome and Firefox
#   - Chrome and Firefox both accept domain=127.0.0.1 or no domain at all for a page on 127.0.0.1
# Plain http is required, as an https page would need a CONNECT tunnel to the proxy.


@pytest.fixture(
    params=[
        {"name": "session_id", "value": "abc123", "domain": "example.com", "path": "/"},
        {"name": "user_token", "value": "xyz789", "domain": "example.com", "path": "/"},
    ],
    ids=["session_id", "user_token"],
    scope="module",
)
def cookie_data(request: FixtureRequest) -> dict[str, str]:
    return request.param


@pytest.fixture
def clean_session(session: requestium.Session, server: LocalServer) -> Generator[requestium.Session, None, None]:
    """Ensure cookies are cleared before each test, and let requests reach fake public hosts through the local server."""
    session.cookies.clear()
    for host in ("example.com", "example.net"):
        session.driver.get(f"http://{host}")  # the driver only deletes cookies of the current page's domain
        session.driver.delete_all_cookies()
    session._last_requests_url = None
    session.proxies.update(server.proxies)
    yield session
    session.proxies.clear()


def assert_first_cookie_matches(driver_cookies: list[dict], expected: dict[str, str]) -> None:
    """Verify the first cookie in a list matches expected values."""
    assert len(driver_cookies) == 1

    cookie = driver_cookies[0]
    assert cookie["name"] == expected["name"]
    assert cookie["value"] == expected["value"]
    assert cookie["domain"] in {expected["domain"], f".{expected['domain']}"}
    assert cookie["path"] == expected["path"]


def echoed_cookies(session: requestium.Session, host: str) -> str:
    """Return the Cookie header the server received when the session fetched the host."""
    return session.get(f"http://{host}/echo").json()["cookies"]


def cookies_sent_by_driver(session: requestium.Session) -> str:
    """Return the Cookie header the server received when the browser fetched http://example.com/echo."""
    session.driver.get("http://example.com")
    echo = session.driver.execute_async_script("fetch('/echo').then((r) => r.json()).then(arguments[0]);")
    return echo["cookies"]


def test_ensure_add_cookie(clean_session: requestium.Session, cookie_data: dict[str, str]) -> None:
    clean_session.driver.ensure_add_cookie(cookie_data)

    assert_first_cookie_matches(clean_session.driver.get_cookies(), cookie_data)


def test_ensure_add_cookie_is_sent_to_server(clean_session: requestium.Session, cookie_data: dict[str, str]) -> None:
    clean_session.driver.ensure_add_cookie(cookie_data)

    sent = cookies_sent_by_driver(clean_session)
    assert sent == f"{cookie_data['name']}={cookie_data['value']}"


def test_ensure_add_cookie_domain_override(clean_session: requestium.Session, cookie_data: dict[str, str]) -> None:
    override_domain = "example.net"

    clean_session.driver.ensure_add_cookie(cookie_data, override_domain=override_domain)

    expected = {**cookie_data, "domain": override_domain}
    assert_first_cookie_matches(clean_session.driver.get_cookies(), expected)


def test_ensure_add_cookie_falls_back_to_parent_domain(clean_session: requestium.Session) -> None:
    """www.example.com redirects to example.com, so the cookie for www is rejected until retried with the parent domain."""
    cookie = {"name": "fallback", "value": "1", "domain": "www.example.com", "path": "/"}

    clean_session.driver.ensure_add_cookie(cookie)

    assert clean_session.driver.current_url == "http://example.com/"
    assert_first_cookie_matches(clean_session.driver.get_cookies(), {**cookie, "domain": "example.com"})


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

"""RequestiumResponse behavior over real HTTP against the local server (no browser needed)."""

import json
import pickle

import pytest
import requests

import requestium
from requestium.requestium_response import RequestiumResponse

from .conftest import LocalServer

LATIN1_HTML = "<html><body><p class='w'>café crème</p></body></html>"


@pytest.fixture(scope="module")
def base_url(server: LocalServer) -> str:
    server.add_page("/html", "<html><body><h1>Title</h1><p class='n'>one 11</p><p class='n'>two 22</p></body></html>")
    server.add_page("/latin1", LATIN1_HTML.encode("latin-1"), content_type="text/html; charset=latin-1")
    server.add_page("/json", json.dumps({"a": [1, 2]}), content_type="application/json")
    server.add_page("/hop", "", status=302, headers={"Location": "/final", "Set-Cookie": "hop=1; Path=/"})
    server.add_page("/final", "<p>done</p>", status=201, headers={"X-Custom": "yes", "Set-Cookie": "final=2; Path=/"})
    return server.url


@pytest.fixture(scope="module")
def plain_session() -> requestium.Session:
    # No browser is started: the driver is created lazily.
    return requestium.Session()


def test_xpath_css_re(plain_session: requestium.Session, base_url: str) -> None:
    response = plain_session.get(base_url + "/html")
    assert response.xpath("//h1/text()").get() == "Title"
    assert response.css("p.n::text").getall() == ["one 11", "two 22"]
    assert response.re(r"(\d\d)") == ["11", "22"]
    assert response.re_first(r"(\d\d)") == "11"


def test_re_first_default_and_empty_results(plain_session: requestium.Session, base_url: str) -> None:
    response = plain_session.get(base_url + "/html")
    assert response.re_first(r"(\d{5})") is None
    assert response.re_first(r"(\d{5})", default="none") == "none"
    assert response.re(r"(\d{5})") == []
    assert response.xpath("//table").get() is None
    assert response.xpath("//table").get(default="x") == "x"
    assert response.css("table") == []


def test_non_utf8_encoding_parses_correctly(plain_session: requestium.Session, base_url: str) -> None:
    response = plain_session.get(base_url + "/latin1")
    assert response.encoding == "latin-1"
    assert response.xpath("//p/text()").get() == "café crème"
    assert response.re_first(r"caf(.)") == "é"


def test_selector_reparses_when_encoding_changes(plain_session: requestium.Session, base_url: str) -> None:
    response = plain_session.get(base_url + "/latin1")
    assert response.css("p.w::text").get() == "café crème"
    response.encoding = "utf-8"
    # Mis-decoding as utf-8 replaces the invalid latin-1 bytes, so a stale cached selector would still show "café".
    assert response.css("p.w::text").get() == "caf� cr�me"
    response.encoding = "latin-1"
    assert response.css("p.w::text").get() == "café crème"


def test_json(plain_session: requestium.Session, base_url: str) -> None:
    response = plain_session.get(base_url + "/json")
    assert response.json() == {"a": [1, 2]}


def test_is_a_requests_response(plain_session: requestium.Session, base_url: str) -> None:
    response = plain_session.get(base_url + "/html")
    assert isinstance(response, requests.Response)
    assert isinstance(response, RequestiumResponse)
    assert response.ok
    assert response.content.startswith(b"<html>")
    assert "Title" in response.text
    response.raise_for_status()


def test_raise_for_status_on_error(plain_session: requestium.Session, base_url: str) -> None:
    response = plain_session.get(base_url + "/missing")
    assert response.status_code == 404
    with pytest.raises(requests.HTTPError):
        response.raise_for_status()


def test_status_headers_cookies_history_after_redirect(plain_session: requestium.Session, base_url: str) -> None:
    response = plain_session.get(base_url + "/hop")
    assert response.status_code == 201
    assert response.url == base_url + "/final"
    assert response.headers["X-Custom"] == "yes"
    assert response.cookies["final"] == "2"
    assert [r.status_code for r in response.history] == [302]
    assert response.history[0].cookies["hop"] == "1"
    assert response.request.url == base_url + "/final"
    assert response.xpath("//p/text()").get() == "done"


def test_pickle_roundtrip(plain_session: requestium.Session, base_url: str) -> None:
    response = plain_session.get(base_url + "/html")
    restored = pickle.loads(pickle.dumps(response))
    assert isinstance(restored, RequestiumResponse)
    assert restored.status_code == 200
    assert restored.css("h1::text").get() == "Title"

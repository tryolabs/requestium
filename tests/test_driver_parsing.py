import requestium.requestium

from .conftest import LocalServer


def test_xpath(session: requestium.Session, example_url: str) -> None:
    session.driver.get(example_url)

    assert session.driver.xpath("//h1/text()").get() == "Test Header 1"
    assert session.driver.xpath("//a/@href").getall() == ["example.com", "example.com"]
    assert session.driver.xpath("//a[@name='link-paragraph']/text()").get() == "Test Link 1"
    assert not session.driver.xpath("//table")


def test_css(session: requestium.Session, example_url: str) -> None:
    session.driver.get(example_url)

    assert session.driver.css("#test-header::text").get() == "Test Header 2"
    assert session.driver.css("p.body-text::text").get() == "Test Paragraph 1"
    assert session.driver.css("a::text").getall() == ["Test Link 1", "Test Link 2"]
    assert not session.driver.css("table")


def test_re(session: requestium.Session, example_url: str) -> None:
    session.driver.get(example_url)

    assert session.driver.re(r"Test Header (\d)") == ["1", "2", "3"]
    assert session.driver.re(r"no such text") == []


def test_re_first(session: requestium.Session, example_url: str) -> None:
    session.driver.get(example_url)

    assert session.driver.re_first(r"Test Header (\d)") == "1"
    assert session.driver.re_first(r"no such text") is None


def test_selector_reflects_current_page_state(session: requestium.Session, example_url: str, server: LocalServer) -> None:
    """Parsing is never cached: DOM changes made by javascript show up in the next call."""
    session.driver.get(example_url)
    assert session.driver.css("h1::text").get() == "Test Header 1"

    session.driver.execute_script("document.querySelector('h1').textContent = 'Changed by JS';")
    assert session.driver.css("h1::text").get() == "Changed by JS"
    assert session.driver.selector.css("h1::text").get() == "Changed by JS"

    session.driver.get(server.add_page("/other", "<html><body><h1>Other Page</h1></body></html>"))
    assert session.driver.css("h1::text").get() == "Other Page"

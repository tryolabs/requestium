from selenium.webdriver.remote.webelement import WebElement

import requestium.requestium


def test_ensure_element_by_id(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_id("test-header")
    assert isinstance(element, WebElement)
    assert element.text == "Test Header 2"


def test_ensure_element_by_name(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_name("link-paragraph")
    assert isinstance(element, WebElement)
    assert element.text == "Test Link 1"


def test_ensure_element_by_xpath(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_xpath("//a[text()='Test Link 2']")
    assert isinstance(element, WebElement)
    assert element.text == "Test Link 2"


def test_ensure_element_by_link_text(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_link_text("Test Link 1")
    assert isinstance(element, WebElement)
    assert element.text == "Test Link 1"


def test_ensure_element_by_partial_link_text(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_partial_link_text("Link 2")
    assert isinstance(element, WebElement)
    assert element.text == "Test Link 2"


def test_ensure_element_by_tag_name(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_tag_name("h1")
    assert isinstance(element, WebElement)
    assert element.text == "Test Header 1"


def test_ensure_element_by_class_name(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_class_name("body-text")
    assert isinstance(element, WebElement)
    assert element.text == "Test Paragraph 1"


def test_ensure_element_by_css_selector(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_css_selector(".body-text")
    assert isinstance(element, WebElement)
    assert element.text == "Test Paragraph 1"


def test_simple_page_load(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    title = session.driver.title
    assert title == "The Internet"

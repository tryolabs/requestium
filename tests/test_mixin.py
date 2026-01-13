from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By, ByType
from selenium.webdriver.remote.webelement import WebElement

import requestium.requestium


def assert_webelement_text_exact_match(element: WebElement | None, expected: str) -> None:
    """Verify the provided element is a WebElement with matching text."""
    assert isinstance(element, WebElement)
    assert element.text == expected


def test_ensure_element_by_id(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_id("test-header")
    assert_webelement_text_exact_match(element, "Test Header 2")


def test_ensure_element_by_name(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_name("link-paragraph")
    assert_webelement_text_exact_match(element, "Test Link 1")


def test_ensure_element_by_xpath(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_xpath("//a[text()='Test Link 2']")
    assert_webelement_text_exact_match(element, "Test Link 2")


def test_ensure_element_by_link_text(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_link_text("Test Link 1")
    assert_webelement_text_exact_match(element, "Test Link 1")


def test_ensure_element_by_partial_link_text(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_partial_link_text("Link 2")
    assert_webelement_text_exact_match(element, "Test Link 2")


def test_ensure_element_by_tag_name(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_tag_name("h1")
    assert_webelement_text_exact_match(element, "Test Header 1")


def test_ensure_element_by_class_name(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_class_name("body-text")
    assert_webelement_text_exact_match(element, "Test Paragraph 1")


def test_ensure_element_by_css_selector(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_css_selector(".body-text")
    assert_webelement_text_exact_match(element, "Test Paragraph 1")


@pytest.mark.parametrize(
    ("locator", "selector", "result"),
    [
        (By.ID, "test-header", "Test Header 2"),
        (By.NAME, "link-paragraph", "Test Link 1"),
        (By.XPATH, "//a[text()='Test Link 2']", "Test Link 2"),
        (By.LINK_TEXT, "Test Link 1", "Test Link 1"),
        (By.PARTIAL_LINK_TEXT, "Link 2", "Test Link 2"),
        (By.TAG_NAME, "h1", "Test Header 1"),
        (By.CLASS_NAME, "body-text", "Test Paragraph 1"),
        (By.CSS_SELECTOR, ".body-text", "Test Paragraph 1"),
        (By.CSS_SELECTOR, "#test-header", "Test Header 2"),
    ],
    ids=["id", "name", "xpath", "link_text", "partial_link_text", "tag_name", "class_name", "css_selector_class", "css_selector_id"],
)
def test_ensure_element(session: requestium.Session, example_html: str, locator: ByType, selector: str, result: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element(locator=locator, selector=selector)
    assert_webelement_text_exact_match(element, result)

    element = session.driver.ensure_element(locator, selector)
    assert_webelement_text_exact_match(element, result)


def test_deprecation_warning_for_ensure_element_locators_with_underscores(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")
    with pytest.warns(DeprecationWarning, match="Support for locator strategy names with underscores is deprecated"):
        session.driver.ensure_element(locator="tag_name", selector="h1")
    with pytest.warns(DeprecationWarning, match="Support for locator strategy names with underscores is deprecated"):
        session.driver.ensure_element("tag_name", "h1")


def test_simple_page_load(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    session.driver.ensure_element_by_tag_name("h1")  # wait for page load
    title = session.driver.title
    assert title == "The Internet"


def test_ensure_click(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")

    element = session.driver.ensure_element_by_tag_name("button")
    assert isinstance(element, WebElement)
    requestium.requestium._ensure_click(element)

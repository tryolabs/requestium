import pytest
from selenium.webdriver.common.by import By, ByType
from selenium.webdriver.remote.webelement import WebElement

import requestium.requestium

LOCATORS = [
    pytest.param(By.ID, "test-header", "Test Header 2", id="id"),
    pytest.param(By.NAME, "link-paragraph", "Test Link 1", id="name"),
    pytest.param(By.XPATH, "//a[text()='Test Link 2']", "Test Link 2", id="xpath"),
    pytest.param(By.LINK_TEXT, "Test Link 1", "Test Link 1", id="link_text"),
    pytest.param(By.PARTIAL_LINK_TEXT, "Link 2", "Test Link 2", id="partial_link_text"),
    pytest.param(By.TAG_NAME, "h1", "Test Header 1", id="tag_name"),
    pytest.param(By.CLASS_NAME, "body-text", "Test Paragraph 1", id="class_name"),
    pytest.param(By.CSS_SELECTOR, ".body-text", "Test Paragraph 1", id="css_selector_class"),
    pytest.param(By.CSS_SELECTOR, "#test-header", "Test Header 2", id="css_selector_id"),
]


def assert_webelement_text_exact_match(element: WebElement | None, expected: str) -> None:
    """Verify the provided element is a WebElement with matching text."""
    assert isinstance(element, WebElement)
    assert element.text == expected


@pytest.mark.parametrize(("locator", "selector", "result"), LOCATORS)
def test_ensure_element(session: requestium.Session, example_url: str, locator: ByType, selector: str, result: str) -> None:
    session.driver.get(example_url)

    assert_webelement_text_exact_match(session.driver.ensure_element(locator=locator, selector=selector), result)
    assert_webelement_text_exact_match(session.driver.ensure_element(locator, selector), result)


@pytest.mark.parametrize(
    ("method", "selector", "result"),
    [
        ("ensure_element_by_id", "test-header", "Test Header 2"),
        ("ensure_element_by_name", "link-paragraph", "Test Link 1"),
        ("ensure_element_by_xpath", "//a[text()='Test Link 2']", "Test Link 2"),
        ("ensure_element_by_link_text", "Test Link 1", "Test Link 1"),
        ("ensure_element_by_partial_link_text", "Link 2", "Test Link 2"),
        ("ensure_element_by_tag_name", "h1", "Test Header 1"),
        ("ensure_element_by_class_name", "body-text", "Test Paragraph 1"),
        ("ensure_element_by_css_selector", ".body-text", "Test Paragraph 1"),
    ],
)
def test_ensure_element_by_wrappers(session: requestium.Session, example_url: str, method: str, selector: str, result: str) -> None:
    session.driver.get(example_url)

    assert_webelement_text_exact_match(getattr(session.driver, method)(selector), result)


def test_ensure_element_by_wrapper_passes_state_and_timeout(session: requestium.Session, example_url: str) -> None:
    session.driver.get(example_url)

    assert session.driver.ensure_element_by_id("no-such-id", state="invisible", timeout=0.3) is None


def test_ensure_element_adds_ensure_click(session: requestium.Session, example_url: str) -> None:
    session.driver.get(example_url)

    element = session.driver.ensure_element_by_tag_name("button")
    assert callable(element.ensure_click)  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("legacy_locator", "selector", "result"),
    [
        ("link_text", "Test Link 1", "Test Link 1"),
        ("partial_link_text", "Link 2", "Test Link 2"),
        ("tag_name", "h1", "Test Header 1"),
        ("class_name", "body-text", "Test Paragraph 1"),
        ("css_selector", ".body-text", "Test Paragraph 1"),
    ],
)
def test_deprecation_warning_for_ensure_element_locators_with_underscores(
    session: requestium.Session, example_url: str, legacy_locator: str, selector: str, result: str
) -> None:
    session.driver.get(example_url)

    with pytest.warns(DeprecationWarning, match="Support for locator strategy names with underscores is deprecated"):
        assert_webelement_text_exact_match(session.driver.ensure_element(locator=legacy_locator, selector=selector), result)
    with pytest.warns(DeprecationWarning, match="Support for locator strategy names with underscores is deprecated"):
        assert_webelement_text_exact_match(session.driver.ensure_element(legacy_locator, selector), result)


def test_simple_page_load(session: requestium.Session, example_url: str) -> None:
    session.driver.get(example_url)

    session.driver.ensure_element_by_tag_name("h1")  # wait for page load
    assert session.driver.title == "The Internet"

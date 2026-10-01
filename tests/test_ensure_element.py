import time

import pytest
from selenium.common import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

import requestium.requestium

from .conftest import LocalServer

STATE_PAGE = """
<html>
    <body>
        <div id="shown">Shown</div>
        <div id="hidden" style="display: none">Hidden</div>
        <button id="enabled">Enabled</button>
        <button id="disabled" disabled>Disabled</button>
        <div id="late-container"></div>
    </body>
</html>
"""

CLICK_PAGE = """
<html>
    <body>
        <div id="result">not clicked</div>
        <div style="height: 4000px"></div>
        <button id="far-away" onclick="document.getElementById('result').textContent = 'clicked'">Click Me</button>
        <div style="height: 1000px"></div>
        <div style="position: relative">
            <button id="covered" onclick="document.getElementById('result').textContent = 'wrongly clicked'">Covered</button>
            <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%"></div>
        </div>
    </body>
</html>
"""


@pytest.fixture
def state_page(session: requestium.Session, server: LocalServer) -> requestium.Session:
    session.driver.get(server.add_page("/states", STATE_PAGE))
    return session


def run_later(session: requestium.Session, script: str, delay_ms: int = 300) -> None:
    """Run javascript in the page after a delay, so the element changes while ensure_element is waiting."""
    session.driver.execute_script(f"setTimeout(() => {{ {script} }}, {delay_ms});")


@pytest.mark.parametrize(
    ("state", "element_id"),
    [
        ("present", "shown"),
        ("present", "hidden"),
        ("visible", "shown"),
        ("clickable", "enabled"),
    ],
)
def test_state_satisfied(state_page: requestium.Session, state: str, element_id: str) -> None:
    element = state_page.driver.ensure_element(By.ID, element_id, state)

    assert isinstance(element, WebElement)
    assert element.get_attribute("id") == element_id


@pytest.mark.parametrize(
    ("state", "element_id"),
    [
        ("present", "missing"),
        ("visible", "hidden"),
        ("visible", "missing"),
        ("clickable", "disabled"),
        ("clickable", "hidden"),
        ("invisible", "shown"),
    ],
)
def test_state_not_satisfied_times_out(state_page: requestium.Session, state: str, element_id: str) -> None:
    with pytest.raises(TimeoutException):
        state_page.driver.ensure_element(By.ID, element_id, state, timeout=0.3)


@pytest.mark.parametrize("element_id", ["hidden", "missing"])
def test_invisible_returns_none(state_page: requestium.Session, element_id: str) -> None:
    assert state_page.driver.ensure_element(By.ID, element_id, "invisible") is None


def test_invalid_state(state_page: requestium.Session) -> None:
    with pytest.raises(ValueError, match="The 'state' argument must be 'visible', 'clickable', 'present' or 'invisible', not 'bogus'"):
        state_page.driver.ensure_element(By.ID, "shown", "bogus")


def test_state_defaults_to_present(state_page: requestium.Session) -> None:
    element = state_page.driver.ensure_element(By.ID, "hidden")

    assert isinstance(element, WebElement)


def test_element_appearing_later(state_page: requestium.Session) -> None:
    assert not state_page.driver.find_elements(By.ID, "late")

    run_later(state_page, "const e = document.createElement('div'); e.id = 'late'; e.textContent = 'Late'; document.body.appendChild(e);")
    element = state_page.driver.ensure_element(By.ID, "late", "visible", timeout=5)

    assert isinstance(element, WebElement)
    assert element.text == "Late"


def test_element_becoming_visible_later(state_page: requestium.Session) -> None:
    run_later(state_page, "document.getElementById('hidden').style.display = 'block';")
    element = state_page.driver.ensure_element(By.ID, "hidden", "visible", timeout=5)

    assert isinstance(element, WebElement)
    assert element.text == "Hidden"


def test_element_disappearing_later(state_page: requestium.Session) -> None:
    run_later(state_page, "document.getElementById('shown').remove();")

    assert state_page.driver.ensure_element(By.ID, "shown", "invisible", timeout=5) is None
    assert not state_page.driver.find_elements(By.ID, "shown")


def test_element_becoming_enabled_later(state_page: requestium.Session) -> None:
    run_later(state_page, "document.getElementById('disabled').disabled = false;")
    element = state_page.driver.ensure_element(By.ID, "disabled", "clickable", timeout=5)

    assert isinstance(element, WebElement)


def test_timeout_is_honored(state_page: requestium.Session) -> None:
    start = time.monotonic()
    with pytest.raises(TimeoutException):
        state_page.driver.ensure_element(By.ID, "missing", timeout=1)

    assert 1 <= time.monotonic() - start < 4


@pytest.mark.usefixtures("state_page")
def test_session_default_timeout_is_used(session: requestium.Session) -> None:
    original_timeout = session.driver.default_timeout
    try:
        # Passing an existing driver to a new Session applies that Session's default_timeout to the driver
        short_session = requestium.Session(driver=session.driver, default_timeout=0.6)
        assert short_session.driver.default_timeout == 0.6

        run_later(short_session, "document.body.appendChild(Object.assign(document.createElement('div'), {id: 'slow'}));", delay_ms=1500)
        start = time.monotonic()
        with pytest.raises(TimeoutException):
            short_session.driver.ensure_element(By.ID, "slow")
        assert 0.6 <= time.monotonic() - start < 1.4

        # An explicit timeout overrides the default
        assert short_session.driver.ensure_element(By.ID, "slow", timeout=5) is not None
    finally:
        session.driver.default_timeout = original_timeout


def test_ensure_click(state_page: requestium.Session, server: LocalServer) -> None:
    driver = state_page.driver
    driver.get(server.add_page("/click", CLICK_PAGE))

    button = driver.ensure_element(By.ID, "far-away", "clickable")
    assert isinstance(button, WebElement)
    assert driver.execute_script("return window.scrollY;") == 0

    button.ensure_click()  # type: ignore[attr-defined]

    assert driver.find_element(By.ID, "result").text == "clicked"
    assert driver.execute_script("return window.scrollY;") > 0


def test_ensure_click_gives_up_on_unclickable_element(state_page: requestium.Session, server: LocalServer) -> None:
    driver = state_page.driver
    driver.get(server.add_page("/click", CLICK_PAGE))

    covered = driver.ensure_element(By.ID, "covered", "present")
    assert isinstance(covered, WebElement)

    with pytest.raises(WebDriverException, match="Couldn't click item after trying 10 times"):
        covered.ensure_click()  # type: ignore[attr-defined]

    assert driver.find_element(By.ID, "result").text == "not clicked"

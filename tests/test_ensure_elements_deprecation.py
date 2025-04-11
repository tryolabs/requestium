import pytest


def test_deprecation_warning_for_ensure_element_locators_with_underscores(session):
    session.driver.get("https://the-internet.herokuapp.com")
    with pytest.warns(DeprecationWarning):
        session.driver.ensure_element("class_name", "no-js")

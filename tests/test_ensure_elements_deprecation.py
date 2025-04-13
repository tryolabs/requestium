import pytest
import requestium

from test_requestium import session_parameters


@pytest.mark.parametrize("params", session_parameters)
def test_deprecation_warning_for_ensure_element_locators_with_underscores(params) -> None:
    with requestium.Session(**params) as session:
        session.driver.get("http://the-internet.herokuapp.com")
        with pytest.warns(DeprecationWarning):
            session.driver.ensure_element("class_name", "no-js")

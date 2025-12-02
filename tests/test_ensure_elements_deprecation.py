import pytest

import requestium.requestium


def test_deprecation_warning_for_ensure_element_locators_with_underscores(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")
    with pytest.warns(DeprecationWarning):
        session.driver.ensure_element("tag_name", "h1")

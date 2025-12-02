from selenium.webdriver.common.by import By

import requestium.requestium


def test_simple_page_load(session: requestium.Session, example_html: str) -> None:
    session.driver.get(f"data:text/html,{example_html}")
    session.driver.ensure_element(By.TAG_NAME, "h1")

    title = session.driver.title
    heading = session.driver.find_element(By.TAG_NAME, "h1")

    assert title == "The Internet"
    assert heading.text == "Test Page"

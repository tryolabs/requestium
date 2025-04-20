from selenium.webdriver.common.by import By

import requestium.requestium


def test_simple_page_load(session: requestium.Session) -> None:
    session.driver.get("http://the-internet.herokuapp.com")
    session.driver.ensure_element(By.ID, "content")

    title = session.driver.title
    heading = session.driver.find_element(By.XPATH, '//*[@id="content"]/h1')

    assert title == "The Internet"
    assert heading.text == "Welcome to the-internet"

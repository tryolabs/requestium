from __future__ import annotations

import functools
import time
import warnings
from typing import TYPE_CHECKING, Any

import tldextract
from parsel.selector import Selector, SelectorList
from selenium.common.exceptions import NoSuchWindowException, WebDriverException
from selenium.webdriver.common.by import By, ByType
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from selenium.webdriver.remote.webelement import WebElement


DEFAULT_TIMEOUT: float = 0.5


def _ensure_click(self: WebElement) -> None:
    """
    Ensure a click gets made, because Selenium can be a bit buggy about clicks.

    This method gets added to the selenium element returned in '__ensure_element_by_xpath'.
    We should probably add it to more selenium methods, such as all the 'find**' methods though.

    I wrote this method out of frustration with chromedriver and its problems with clicking
    items that need to be scrolled to in order to be clickable. In '__ensure_element_by_xpath' we
    scroll to the item before returning it, but chrome has some problems if it doesn't get some
    time to scroll to the item. This method ensures chromes gets enough time to scroll to the item
    before clicking it. I tried SEVERAL more 'correct' methods to get around this, but none of them
    worked 100% of the time (waiting for the element to be 'clickable' does not work).
    """
    # We ensure the element is scrolled into the middle of the viewport to ensure that
    # it is clickable. There are two main ways an element may not be clickable:
    #   - It is outside of the viewport
    #   - It is under a banner or toolbar
    # This script solves both cases
    script = (
        "var viewPortHeight = Math.max("
        "document.documentElement.clientHeight, window.innerHeight || 0);"
        "var elementTop = arguments[0].getBoundingClientRect().top;"
        "window.scrollBy(0, elementTop-(viewPortHeight/2));"
    )
    self.parent.execute_script(script, self)  # parent = the webdriver

    exception_message = ""
    for _ in range(10):
        try:
            self.click()
            return
        except WebDriverException as e:
            exception_message = str(e)
            time.sleep(0.2)
    msg = f"Couldn't click item after trying 10 times, got error message: \n{exception_message}"
    raise WebDriverException(msg)


class DriverMixin(RemoteWebDriver):
    """Provides helper methods to our driver classes."""

    def __init__(self, *args, **kwargs) -> None:
        self.default_timeout = kwargs.pop("default_timeout", DEFAULT_TIMEOUT)
        super().__init__(*args, **kwargs)

    def try_add_cookie(self, cookie: dict[str, Any]) -> bool:
        """
        Attempt to add the cookie.

        Suppress any errors, and simply detect success or failure.
        """
        try:
            self.add_cookie(cookie)
        except WebDriverException as e:
            if e.msg and not e.msg.__contains__("Couldn't add the following cookie to the webdriver"):
                raise WebDriverException from e
        return self.is_cookie_in_driver(cookie)

    def ensure_add_cookie(self, cookie: dict[str, Any], override_domain: str | None = None) -> None:
        """
        Add a cookie to the driver and check to ensure it has been added.

        Selenium needs the driver to be currently at the domain of the cookie
        before allowing you to add it, so we need to get through this limitation.

        The cookie parameter is a dict which must contain the keys (name, value, domain) and
        may contain the keys (path, expiry).

        We first check that we aren't currently in the cookie's domain, if we aren't, we GET
        the cookie's domain and then add the cookies to the driver.

        We can override the cookie's domain using 'override_domain'. The use for this
        parameter is that sometimes GETting the cookie's domain redirects you to a different
        sub domain, and therefore adding the cookie fails. So sometimes the user may
        need to override the cookie's domain to a less strict one, Eg.: 'site.com' instead of
        'home.site.com', in this way even if the site redirects us to a subdomain, the cookie will
        stick. If you set the domain to '', the cookie gets added with whatever domain the browser
        is currently at (at least in chrome it does), so this ensures the cookie gets added.

        It also retries adding the cookie with a more permissive domain if it fails in the first
        try, and raises an exception if that fails. The standard selenium behaviour in this case
        was to not do anything, which was very hard to debug.
        """
        if override_domain:
            cookie["domain"] = override_domain

        cookie_domain = cookie["domain"] if cookie["domain"][0] != "." else cookie["domain"][1:]
        try:
            browser_domain = tldextract.extract(self.current_url).fqdn
        except (AttributeError, NoSuchWindowException):
            browser_domain = ""
        if cookie_domain not in browser_domain:
            # TODO @joaqo: Check if hardcoding 'http' causes trouble.
            # https://github.com/tryolabs/requestium/issues/97
            # Consider using a new proxy for this next request to not cause an anomalous
            # request. This way their server sees our ip address as continuously having the
            # same cookies and not have a request mid-session with no cookies
            self.get("http://" + cookie_domain)

        cookie_added = self.try_add_cookie(cookie)

        # If we fail adding the cookie, retry with a more permissive domain
        if not cookie_added:
            cookie["domain"] = tldextract.extract(cookie["domain"]).top_domain_under_public_suffix
            cookie_added = self.try_add_cookie(cookie)
            if not cookie_added:
                msg = f"Couldn't add the following cookie to the webdriver: {cookie}"
                raise WebDriverException(msg)

    def is_cookie_in_driver(self, cookie: dict[str, Any]) -> bool:
        """
        We check that the cookie is correctly added to the driver.

        We only compare name, value and domain, as the rest can produce false negatives.
        We are a bit lenient when comparing domains.
        """
        for driver_cookie in self.get_cookies():
            name_matches = cookie["name"] == driver_cookie["name"]
            value_matches = cookie["value"] == driver_cookie["value"]
            domain_matches = driver_cookie["domain"] in (cookie["domain"], "." + cookie["domain"])
            if name_matches and value_matches and domain_matches:
                return True
        return False

    def ensure_element_by_id(self, selector: str, state: str | None = "present", timeout: float | None = None) -> WebElement | None:
        return self.ensure_element(By.ID, selector, state, timeout)

    def ensure_element_by_name(self, selector: str, state: str | None = "present", timeout: float | None = None) -> WebElement | None:
        return self.ensure_element(By.NAME, selector, state, timeout)

    def ensure_element_by_xpath(self, selector: str, state: str | None = "present", timeout: float | None = None) -> WebElement | None:
        return self.ensure_element(By.XPATH, selector, state, timeout)

    def ensure_element_by_link_text(self, selector: str, state: str | None = "present", timeout: float | None = None) -> WebElement | None:
        return self.ensure_element(By.LINK_TEXT, selector, state, timeout)

    def ensure_element_by_partial_link_text(self, selector: str, state: str | None = "present", timeout: float | None = None) -> WebElement | None:
        return self.ensure_element(By.PARTIAL_LINK_TEXT, selector, state, timeout)

    def ensure_element_by_tag_name(self, selector: str, state: str | None = "present", timeout: float | None = None) -> WebElement | None:
        return self.ensure_element(By.TAG_NAME, selector, state, timeout)

    def ensure_element_by_class_name(self, selector: str, state: str | None = "present", timeout: float | None = None) -> WebElement | None:
        return self.ensure_element(By.CLASS_NAME, selector, state, timeout)

    def ensure_element_by_css_selector(self, selector: str, state: str | None = "present", timeout: float | None = None) -> WebElement | None:
        return self.ensure_element(By.CSS_SELECTOR, selector, state, timeout)

    def ensure_element(self, locator: ByType | str, selector: str, state: str | None = "present", timeout: float | None = None) -> WebElement | None:
        """
        Wait until an element appears or disappears in the browser.

        The webdriver runs in parallel with our scripts, so we must wait for it everytime it
        runs javascript. Selenium automatically waits till a page loads when GETing it,
        but it doesn't do this when it runs javascript and makes AJAX requests.
        So we must explicitly wait in that case.

        The 'locator' argument defines what strategy we use to search for the element.
        It expects standard names from the By class in selenium.webdriver.common.by.
        https://www.selenium.dev/selenium/docs/api/py/webdriver/selenium.webdriver.common.by.html

        The 'state' argument allows us to chose between waiting for the element to be visible,
        clickable, present, or invisible. Presence is more inclusive, but sometimes we want to
        know if the element is visible. Careful, its not always intuitive what Selenium considers
        to be a visible element. We can also wait for it to be clickable, although this method
        is a bit buggy in selenium, an element can be 'clickable' according to selenium and
        still fail when we try to click it.

        More info at: http://selenium-python.readthedocs.io/waits.html
        """
        locators_compatibility = {
            "link_text": By.LINK_TEXT,
            "partial_link_text": By.PARTIAL_LINK_TEXT,
            "tag_name": By.TAG_NAME,
            "class_name": By.CLASS_NAME,
            "css_selector": By.CSS_SELECTOR,
        }
        if locator in locators_compatibility:
            warnings.warn(
                """
                Support for locator strategy names with underscores is deprecated.
                Use strategies from Selenium's By class (importable from selenium.webdriver.common.by).
                """,
                DeprecationWarning,
                stacklevel=2,
            )
            locator = locators_compatibility[locator]

        if not timeout:
            timeout = self.default_timeout or DEFAULT_TIMEOUT

        if state == "visible":
            element = WebDriverWait(self, timeout).until(expected_conditions.visibility_of_element_located((locator, selector)))
        elif state == "clickable":
            element = WebDriverWait(self, timeout).until(expected_conditions.element_to_be_clickable((locator, selector)))
        elif state == "present":
            element = WebDriverWait(self, timeout).until(expected_conditions.presence_of_element_located((locator, selector)))
        elif state == "invisible":
            WebDriverWait(self, timeout).until(expected_conditions.invisibility_of_element_located((locator, selector)))
            element = None
        else:
            msg = f"The 'state' argument must be 'visible', 'clickable', 'present' or 'invisible', not '{state}'"
            raise ValueError(msg)

        # We add this method to our element to provide a more robust click. Chromedriver
        # sometimes needs some time before it can click an item, specially if it needs to
        # scroll into it first. This method ensures clicks don't fail because of this.
        if element:
            element.ensure_click = functools.partial(_ensure_click, element)  # type: ignore[attr-defined]
        return element

    @property
    def selector(self) -> Selector:
        """
        Returns the current state of the browser in a Selector.

        We re-parse the site on each xpath, css, re call because we are running a web browser
        and the site may change between calls
        """
        return Selector(text=self.page_source)

    def xpath(self, *args, **kwargs) -> SelectorList[Selector]:
        return self.selector.xpath(*args, **kwargs)

    def css(self, *args, **kwargs) -> SelectorList[Selector]:
        return self.selector.css(*args, **kwargs)

    def re(self, *args, **kwargs) -> list[str]:
        return self.selector.re(*args, **kwargs)

    def re_first(self, *args, **kwargs) -> str | None:
        return self.selector.re_first(*args, **kwargs)

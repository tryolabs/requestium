from __future__ import annotations

import functools
import types
from typing import Any

import requests
import tldextract
from selenium import webdriver
from selenium.common import InvalidCookieDomainException
from selenium.webdriver import ChromeService

from .requestium_mixin import DriverMixin
from .requestium_response import RequestiumResponse

RequestiumChrome = type("RequestiumChrome", (DriverMixin, webdriver.Chrome), {})


class Session(requests.Session):
    """
    Class that adds a Selenium Webdriver and helper methods to a  Requests Session.

    This session class is a normal Requests Session that has the ability to switch back
    and forth between this session and a webdriver, allowing us to run js when needed.

    Cookie transfer is done with the 'transfer' methods.

    Header and proxy transfer is done only one time when the driver process starts.

    Some useful helper methods and object wrappings have been added.
    """

    def _start_chrome_browser(self, headless: bool | None = False):  # noqa C901
        # TODO @joaqo: Transfer of proxies and headers.
        # https://github.com/tryolabs/requestium/issues/96
        # Not currently supported by chromedriver. Choosing not to use plug-ins
        # for this as I don't want to worry about the extra dependencies and
        # plug-ins don't work in headless mode. :-(
        chrome_options = webdriver.ChromeOptions()

        if headless:
            chrome_options.add_argument("headless=new")

        if "binary_location" in self.webdriver_options:
            chrome_options.binary_location = self.webdriver_options["binary_location"]

        if "arguments" in self.webdriver_options:
            if isinstance(self.webdriver_options["arguments"], list):
                for arg in self.webdriver_options["arguments"]:
                    chrome_options.add_argument(arg)
            else:
                msg = f"'arguments' option must be a list, but got {type(self.webdriver_options['arguments']).__name__}"
                raise TypeError(msg)

        if "extensions" in self.webdriver_options and isinstance(self.webdriver_options["extensions"], list):
            for arg in self.webdriver_options["extensions"]:
                chrome_options.add_extension(arg)

        if "prefs" in self.webdriver_options:
            prefs = self.webdriver_options["prefs"]
            chrome_options.add_experimental_option("prefs", prefs)

        experimental_options = self.webdriver_options.get("experimental_options")
        if isinstance(experimental_options, dict):
            for name, value in experimental_options.items():
                chrome_options.add_experimental_option(name, value)

        # Selenium updated webdriver.Chrome's arg and kwargs, to accept options, service, keep_alive
        # since ChromeService is the only object where webdriver_path is mapped to executable_path, it must be
        # initialized and passed in as a kwarg to RequestiumChrome so it can be passed in as a kwarg
        # when passed into webdriver.Chrome in super(DriverMixin, self).__init__(*args, **kwargs)
        service = ChromeService(executable_path=self.webdriver_path)
        return RequestiumChrome(service=service, options=chrome_options, default_timeout=self.default_timeout)

    def __init__(
        self,
        *,
        webdriver_path: str | None = None,
        headless: bool | None = None,
        default_timeout: float = 5,
        webdriver_options: dict[str, Any] | None = None,
        driver: DriverMixin | None = None,
    ) -> None:
        super().__init__()

        if webdriver_options is None:
            webdriver_options = {}

        self.webdriver_path = webdriver_path
        self.default_timeout = default_timeout
        self.webdriver_options = webdriver_options
        self._driver = driver
        self._last_requests_url: str | None = None

        if not self._driver:
            self._driver_initializer = functools.partial(self._start_chrome_browser, headless=headless)
        else:
            for name in DriverMixin.__dict__:
                name_private = name.startswith("__") and name.endswith("__")
                name_function = isinstance(DriverMixin.__dict__[name], types.FunctionType)
                name_in_driver = name in dir(self._driver)
                if name_private or not name_function or name_in_driver:
                    continue
                self._driver.__dict__[name] = DriverMixin.__dict__[name].__get__(self._driver)
            self._driver.default_timeout = self.default_timeout

    @property
    def driver(self) -> DriverMixin:
        if self._driver is None:
            self._driver = self._driver_initializer()
        return self._driver

    def transfer_session_cookies_to_driver(self, domain: str | None = None) -> None:
        """
        Copy the Session's cookies into the webdriver.

        Using the 'domain' parameter we choose the cookies we wish to transfer, we only
        transfer the cookies which belong to that domain. The domain defaults to our last visited
        site if not provided.
        """
        if not domain and self._last_requests_url:
            domain = tldextract.extract(self._last_requests_url).top_domain_under_public_suffix

        if not domain:
            msg = "Trying to transfer cookies to selenium without specifying a domain and without having visited any page in the current session"
            raise InvalidCookieDomainException(msg)

        # Transfer cookies
        for c in [c for c in self.cookies if domain in c.domain]:
            cookie = {"name": c.name, "value": c.value, "path": c.path, "expiry": c.expires, "domain": c.domain}

            self.driver.ensure_add_cookie({k: v for k, v in cookie.items() if v is not None})

    def transfer_driver_cookies_to_session(self, *, copy_user_agent: bool | None = True) -> None:
        if copy_user_agent:
            self.copy_user_agent_from_driver()

        for cookie in self.driver.get_cookies():
            self.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])

    def get(self, *args, **kwargs) -> RequestiumResponse:
        resp = super().get(*args, **kwargs)
        self._last_requests_url = resp.url
        return RequestiumResponse(resp)

    def post(self, *args, **kwargs) -> RequestiumResponse:
        resp = super().post(*args, **kwargs)
        self._last_requests_url = resp.url
        return RequestiumResponse(resp)

    def put(self, *args, **kwargs) -> RequestiumResponse:
        resp = super().put(*args, **kwargs)
        self._last_requests_url = resp.url
        return RequestiumResponse(resp)

    def copy_user_agent_from_driver(self) -> None:
        """
        Update requests' session user-agent with the driver's user agent.

        This method will start the browser process if its not already running.
        """
        selenium_user_agent = self.driver.execute_script("return navigator.userAgent;")
        self.headers.update({"user-agent": selenium_user_agent})

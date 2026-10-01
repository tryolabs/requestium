from __future__ import annotations

import contextlib
import functools
import warnings
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlsplit

import requests
import tldextract
from requests.cookies import create_cookie
from requests.utils import default_user_agent
from selenium import webdriver
from selenium.common import InvalidCookieDomainException, WebDriverException
from selenium.webdriver import ChromeService

from .requestium_mixin import DriverMixin
from .requestium_response import RequestiumResponse

if TYPE_CHECKING:
    from collections.abc import Callable

    from selenium.webdriver.remote.webdriver import WebDriver

RequestiumChrome = type("RequestiumChrome", (DriverMixin, webdriver.Chrome), {})


@functools.cache
def _mixin_class(base: type) -> type:
    """Return the cached subclass of the given driver class that adds the DriverMixin helpers."""
    return type(f"Requestium{base.__name__}", (DriverMixin, base), {})


def _has_argument(arguments: list[str], name: str) -> bool:
    """Check whether a Chrome command line switch (with or without leading dashes) is already present."""
    return any(arg.lstrip("-").split("=", 1)[0] == name for arg in arguments)


class Session(requests.Session):
    """
    Class that adds a Selenium Webdriver and helper methods to a  Requests Session.

    This session class is a normal Requests Session that has the ability to switch back
    and forth between this session and a webdriver, allowing us to run js when needed.

    Cookie transfer is done with the 'transfer' methods.

    When Requestium starts its own Chrome, the session's proxies (without credentials) and
    custom User-Agent are passed to it as launch arguments. This happens once, when the driver
    is first accessed, so values set on the session before then are honored. Other headers are
    not transferred. Drivers supplied by the user are left as configured.

    Closing the session (or leaving a 'with' block) quits the driver, including a user-supplied one.

    Some useful helper methods and object wrappings have been added.
    """

    def _session_chrome_arguments(self, arguments: list[str]) -> list[str]:
        """Build Chrome arguments carrying over session state, unless the user already supplied them."""
        extra = []

        if not _has_argument(arguments, "proxy-server"):
            proxy_rules = []
            for scheme in ("http", "https"):
                proxy_url = self.proxies.get(scheme)
                if not proxy_url:
                    continue
                parts = urlsplit(proxy_url if "://" in proxy_url else f"http://{proxy_url}")
                if parts.username or parts.password:
                    msg = f"Chrome cannot use proxy credentials passed as arguments, ignoring the '{scheme}' proxy"
                    warnings.warn(msg, stacklevel=4)
                    continue
                server = parts.netloc if parts.scheme == "http" else f"{parts.scheme}://{parts.netloc}"
                proxy_rules.append(f"{scheme}={server}")
            if proxy_rules:
                extra.append(f"--proxy-server={';'.join(proxy_rules)}")

        user_agent = self.headers.get("User-Agent")
        if user_agent and user_agent != default_user_agent() and not _has_argument(arguments, "user-agent"):
            extra.append(f"--user-agent={user_agent!s}")

        return extra

    def _start_chrome_browser(self, *, headless: bool | None = False) -> DriverMixin:  # noqa: C901
        chrome_options = webdriver.ChromeOptions()

        if headless:
            chrome_options.add_argument("headless=new")

        if "binary_location" in self.webdriver_options:
            chrome_options.binary_location = self.webdriver_options["binary_location"]

        arguments: list[str] = []
        if "arguments" in self.webdriver_options:
            if isinstance(self.webdriver_options["arguments"], list):
                arguments = self.webdriver_options["arguments"]
            else:
                msg = f"'arguments' option must be a list, but got {type(self.webdriver_options['arguments']).__name__}"
                raise TypeError(msg)
        for arg in [*arguments, *self._session_chrome_arguments(arguments)]:
            chrome_options.add_argument(arg)

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
        driver: WebDriver | None = None,
    ) -> None:
        super().__init__()

        if webdriver_options is None:
            webdriver_options = {}

        self.webdriver_path = webdriver_path
        self.default_timeout = default_timeout
        self.webdriver_options = webdriver_options
        self._driver: DriverMixin | None = None
        self._driver_initializer: Callable[[], DriverMixin] | None = functools.partial(self._start_chrome_browser, headless=headless)
        self._last_requests_url: str | None = None

        if driver is not None:
            # A user-supplied driver gets the DriverMixin helpers by swapping its class for a subclass that includes them.
            if not isinstance(driver, DriverMixin):
                driver.__class__ = _mixin_class(type(driver))
            self._driver = cast("DriverMixin", driver)
            self._driver.default_timeout = self.default_timeout
            self._driver_initializer = None

    @property
    def driver(self) -> DriverMixin:
        if self._driver is None:
            if self._driver_initializer is None:
                msg = "The user-supplied driver was quit when the session was closed, create a new Session to get a driver"
                raise RuntimeError(msg)
            self._driver = self._driver_initializer()
        return self._driver

    def close(self) -> None:
        """
        Quit the driver, if one was started, and close the underlying Requests session.

        A driver is never started just to close it. For the default Chrome, a later access to
        'driver' starts a fresh one. A user-supplied driver is quit as well and not replaced.
        """
        driver, self._driver = self._driver, None
        if driver is not None:
            with contextlib.suppress(WebDriverException):
                driver.quit()
        super().close()

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
            cookie = {"name": c.name, "value": c.value, "path": c.path, "expiry": c.expires, "domain": c.domain, "secure": c.secure}

            self.driver.ensure_add_cookie({k: v for k, v in cookie.items() if v is not None})

    def transfer_driver_cookies_to_session(self, *, copy_user_agent: bool | None = True) -> None:
        if copy_user_agent:
            self.copy_user_agent_from_driver()

        for cookie in self.driver.get_cookies():
            self.cookies.set_cookie(
                create_cookie(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie["domain"],
                    path=cookie.get("path", "/"),
                    secure=cookie.get("secure", False),
                    expires=cookie.get("expiry"),
                ),
            )

    def request(self, *args, **kwargs) -> RequestiumResponse:
        """Send a request, remembering its final URL and wrapping the response (all HTTP verbs go through here)."""
        resp = super().request(*args, **kwargs)
        self._last_requests_url = resp.url
        return RequestiumResponse(resp)

    if TYPE_CHECKING:
        # Runtime behavior is inherited, since the Requests verbs all call request(); these only narrow the return type.
        def get(self, *args, **kwargs) -> RequestiumResponse: ...
        def options(self, *args, **kwargs) -> RequestiumResponse: ...
        def head(self, *args, **kwargs) -> RequestiumResponse: ...
        def post(self, *args, **kwargs) -> RequestiumResponse: ...
        def put(self, *args, **kwargs) -> RequestiumResponse: ...
        def patch(self, *args, **kwargs) -> RequestiumResponse: ...
        def delete(self, *args, **kwargs) -> RequestiumResponse: ...

    def copy_user_agent_from_driver(self) -> None:
        """
        Update requests' session user-agent with the driver's user agent.

        This method will start the browser process if its not already running.
        """
        selenium_user_agent = self.driver.execute_script("return navigator.userAgent;")
        self.headers.update({"user-agent": selenium_user_agent})

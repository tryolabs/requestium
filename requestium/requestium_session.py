import functools
import types

import requests
import tldextract
from selenium import webdriver
from selenium.webdriver import ChromeService

from .requestium_chrome import RequestiumChrome
from .requestium_response import RequestiumResponse


class Session(requests.Session):
    """
    Class that adds a Selenium Webdriver and helper methods to a  Requests Session

    This session class is a normal Requests Session that has the ability to switch back
    and forth between this session and a webdriver, allowing us to run js when needed.

    Cookie transfer is done with the 'transfer' methods.

    Header and proxy transfer is done only one time when the driver process starts.

    Some useful helper methods and object wrappings have been added.
    """

    def __init__(
        self, webdriver_path: str = None, headless: bool = False, default_timeout: float = 5, webdriver_options: dict = None, driver: webdriver = None
    ) -> None:
        if webdriver_options is None:
            webdriver_options = {}
        super(Session, self).__init__()
        self.webdriver_path = webdriver_path
        self.default_timeout = default_timeout
        self.webdriver_options = webdriver_options
        self._driver = driver
        self._last_requests_url = None

        if self._driver is None:
            self._driver_initializer = functools.partial(self._start_chrome_browser, headless=headless)
        else:
            for name in RequestiumChrome.__dict__:
                name_private = name.startswith("__") and name.endswith("__")
                name_function = isinstance(RequestiumChrome.__dict__[name], types.FunctionType)
                name_in_driver = name in dir(self._driver)
                if name_private or not name_function or name_in_driver:
                    continue
                self._driver.__dict__[name] = RequestiumChrome.__dict__[name].__get__(self._driver)
            self._driver.default_timeout = self.default_timeout

    @property
    def driver(self):
        if self._driver is None:
            self._driver = self._driver_initializer()
        return self._driver

    def _start_chrome_browser(self, headless: bool = False) -> RequestiumChrome:
        # TODO transfer of proxies and headers: Not supported by chromedriver atm.
        # Choosing not to use plug-ins for this as I don't want to worry about the
        # extra dependencies and plug-ins don't work in headless mode. :-(
        chrome_options = webdriver.ChromeOptions()

        if headless:
            chrome_options.add_argument("headless=new")

        if "binary_location" in self.webdriver_options:
            chrome_options.binary_location = self.webdriver_options["binary_location"]

        args = self.webdriver_options.get("arguments")
        if isinstance(args, list):
            [chrome_options.add_argument(arg) for arg in args]
        elif args:
            raise Exception(f"A list is needed to use 'arguments' option. Found {type(args)}")

        extensions = self.webdriver_options.get("extensions")
        if isinstance(extensions, list):
            [chrome_options.add_extension(arg) for arg in extensions]

        if "prefs" in self.webdriver_options:
            prefs = self.webdriver_options["prefs"]
            chrome_options.add_experimental_option("prefs", prefs)

        experimental_options = self.webdriver_options.get("experimental_options")
        if isinstance(experimental_options, dict):
            [chrome_options.add_experimental_option(name, value) for name, value in experimental_options.items()]

        # Selenium updated webdriver.Chrome's arg and kwargs, to accept options, service, keep_alive
        # since ChromeService is the only object where webdriver_path is mapped to executable_path, it must be
        # initialized and passed in as a kwarg to RequestiumChrome so it can be passed in as a kwarg
        # when passed into webdriver.Chrome in super(DriverMixin, self).__init__(*args, **kwargs)
        service = ChromeService(executable_path=self.webdriver_path)
        return RequestiumChrome(
            service=service,
            options=chrome_options,
            default_timeout=self.default_timeout,
        )

    def transfer_session_cookies_to_driver(self, domain: str = None) -> None:
        """
        Copies the Session's cookies into the webdriver

        Using the 'domain' parameter we choose the cookies we wish to transfer, we only
        transfer the cookies which belong to that domain. The domain defaults to our last visited
        site if not provided.
        """
        if not domain and self._last_requests_url:
            domain = tldextract.extract(self._last_requests_url).registered_domain
        elif not domain and not self._last_requests_url:
            raise Exception("Trying to transfer cookies to selenium without specifying a domain " "and without having visited any page in the current session")

        # Transfer cookies
        for c in [c for c in self.cookies if domain in c.domain]:
            cookie = {
                "name": c.name,
                "value": c.value,
                "path": c.path,
                "expiry": c.expires,
                "domain": c.domain,
            }

            self.driver.ensure_add_cookie({k: v for k, v in cookie.items() if v is not None})

    def transfer_driver_cookies_to_session(self, copy_user_agent: bool = True) -> None:
        if copy_user_agent:
            self.copy_user_agent_from_driver()

        for cookie in self.driver.get_cookies():
            self.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])

    def get(self, *args, **kwargs) -> RequestiumResponse:
        resp = super(Session, self).get(*args, **kwargs)
        self._last_requests_url = resp.url
        return RequestiumResponse(resp)

    def post(self, *args, **kwargs) -> RequestiumResponse:
        resp = super(Session, self).post(*args, **kwargs)
        self._last_requests_url = resp.url
        return RequestiumResponse(resp)

    def put(self, *args, **kwargs) -> RequestiumResponse:
        resp = super(Session, self).put(*args, **kwargs)
        self._last_requests_url = resp.url
        return RequestiumResponse(resp)

    def copy_user_agent_from_driver(self) -> None:
        """
        Updates requests' session user-agent with the driver's user agent

        This method will start the browser process if its not already running.
        """
        selenium_user_agent = self.driver.execute_script("return navigator.userAgent;")
        self.headers.update({"user-agent": selenium_user_agent})

import functools
import time
import types

import requests
import tldextract
from parsel.selector import Selector
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait


class Session(requests.Session):
    """Class that adds a Selenium Webdriver and helper methods to a  Requests Session

    This session class is a normal Requests Session that has the ability to switch back
    and forth between this session and a webdriver, allowing us to run js when needed.

    Cookie transfer is done with the 'transfer' methods.

    Header and proxy transfer is done only one time when the driver process starts.

    Some useful helper methods and object wrappings have been added.
    """

    def __init__(self, webdriver_path=None, headless=None, default_timeout=5,
                 webdriver_options={}, driver=None, **kwargs):
        super(Session, self).__init__()
        self.webdriver_path = webdriver_path
        self.default_timeout = default_timeout
        self.webdriver_options = webdriver_options
        self._driver = driver
        self._last_requests_url = None

        if self._driver is None:
            self._driver_initializer = functools.partial(self._start_chrome_browser, headless=headless)
        else:
            for name in DriverMixin.__dict__:
                name_private = name.startswith('__') and name.endswith('__')
                name_function = isinstance(DriverMixin.__dict__[name], types.FunctionType)
                name_in_driver = name in dir(self._driver)
                if name_private or not name_function or name_in_driver:
                    continue
                self._driver.__dict__[name] = DriverMixin.__dict__[name].__get__(self._driver)
            setattr(self._driver, 'default_timeout', self.default_timeout)

    @property
    def driver(self):
        if self._driver is None:
            self._driver = self._driver_initializer()
        return self._driver

    def _start_chrome_browser(self, headless=False):
        # TODO transfer of proxies and headers: Not supported by chromedriver atm.
        # Choosing not to use plug-ins for this as I don't want to worry about the
        # extra dependencies and plug-ins don't work in headless mode. :-(
        chrome_options = webdriver.chrome.options.Options()

        if headless:
            chrome_options.add_argument('headless=new')

        if 'binary_location' in self.webdriver_options:
            chrome_options.binary_location = self.webdriver_options['binary_location']

        if 'arguments' in self.webdriver_options:
            if isinstance(self.webdriver_options['arguments'], list):
                for arg in self.webdriver_options['arguments']:
                    chrome_options.add_argument(arg)
            else:
                raise Exception('A list is needed to use \'arguments\' option. Found {}'.format(
                    type(self.webdriver_options['arguments'])))

        if 'extensions' in self.webdriver_options:
            if isinstance(self.webdriver_options['extensions'], list):
                for arg in self.webdriver_options['extensions']:
                    chrome_options.add_extension(arg)

        if 'prefs' in self.webdriver_options:
            prefs = self.webdriver_options['prefs']
            chrome_options.add_experimental_option('prefs', prefs)

        experimental_options = self.webdriver_options.get('experimental_options')
        if isinstance(experimental_options, dict):
            for name, value in experimental_options.items():
                chrome_options.add_experimental_option(name, value)

        # Create driver process
        RequestiumChrome = type('RequestiumChrome', (DriverMixin, webdriver.Chrome), {})
        # Selenium updated webdriver.Chrome's arg and kwargs, to accept options, service, keep_alive
        # since ChromeService is the only object where webdriver_path is mapped to executable_path, it must be
        # initialized and passed in as a kwarg to RequestiumChrome so it can be passed in as a kwarg
        # when passed into webdriver.Chrome in super(DriverMixin, self).__init__(*args, **kwargs)
        service = ChromeService(executable_path=self.webdriver_path)
        return RequestiumChrome(service=service, options=chrome_options, default_timeout=self.default_timeout)

    def transfer_session_cookies_to_driver(self, domain=None):
        """Copies the Session's cookies into the webdriver

        Using the 'domain' parameter we choose the cookies we wish to transfer, we only
        transfer the cookies which belong to that domain. The domain defaults to our last visited
        site if not provided.
        """
        if not domain and self._last_requests_url:
            domain = tldextract.extract(self._last_requests_url).registered_domain
        elif not domain and not self._last_requests_url:
            raise Exception('Trying to transfer cookies to selenium without specifying a domain '
                            'and without having visited any page in the current session')

        # Transfer cookies
        for c in [c for c in self.cookies if domain in c.domain]:
            cookie = {'name': c.name, 'value': c.value, 'path': c.path,
                      'expiry': c.expires, 'domain': c.domain}

            self.driver.ensure_add_cookie({k: v for k, v in cookie.items() if v is not None})

    def transfer_driver_cookies_to_session(self, copy_user_agent=True):
        if copy_user_agent:
            self.copy_user_agent_from_driver()

        for cookie in self.driver.get_cookies():
            self.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

    def get(self, *args, **kwargs):
        resp = super(Session, self).get(*args, **kwargs)
        self._last_requests_url = resp.url
        return RequestiumResponse(resp)

    def post(self, *args, **kwargs):
        resp = super(Session, self).post(*args, **kwargs)
        self._last_requests_url = resp.url
        return RequestiumResponse(resp)

    def put(self, *args, **kwargs):
        resp = super(Session, self).put(*args, **kwargs)
        self._last_requests_url = resp.url
        return RequestiumResponse(resp)

    def copy_user_agent_from_driver(self):
        """ Updates requests' session user-agent with the driver's user agent

        This method will start the browser process if its not already running.
        """
        selenium_user_agent = self.driver.execute_script("return navigator.userAgent;")
        self.headers.update({"user-agent": selenium_user_agent})


class RequestiumResponse(object):
    """Adds xpath, css, and regex methods to a normal requests response object"""

    def __init__(self, response):
        self.__class__ = type(response.__class__.__name__,
                              (self.__class__, response.__class__),
                              response.__dict__)

    @property
    def selector(self):
        """Returns the response text in a Selector

        We re-parse the text on each xpath, css, re call in case the encoding has changed.
        """
        return Selector(text=self.text)

    def xpath(self, *args, **kwargs):
        return self.selector.xpath(*args, **kwargs)

    def css(self, *args, **kwargs):
        return self.selector.css(*args, **kwargs)

    def re(self, *args, **kwargs):
        return self.selector.re(*args, **kwargs)

    def re_first(self, *args, **kwargs):
        return self.selector.re_first(*args, **kwargs)


class DriverMixin(object):
    """Provides helper methods to our driver classes
    """

    def __init__(self, *args, **kwargs):
        self.default_timeout = kwargs.pop('default_timeout', None)
        super(DriverMixin, self).__init__(*args, **kwargs)

    def try_add_cookie(self, cookie):
        """Attempt to add the cookie. Suppress any errors, and simply
        detect success or failure if the cookie was actually added.
        """
        try:
            self.add_cookie(cookie)
        except Exception:
            pass
        return self.is_cookie_in_driver(cookie)

    def ensure_add_cookie(self, cookie, override_domain=None):
        """Ensures a cookie gets added to the driver

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
            cookie['domain'] = override_domain

        cookie_domain = cookie['domain'] if cookie['domain'][0] != '.' else cookie['domain'][1:]
        try:
            browser_domain = tldextract.extract(self.current_url).fqdn
        except AttributeError:
            browser_domain = ''
        if cookie_domain not in browser_domain:
            # TODO Check if hardcoding 'http' causes trouble
            # TODO Consider using a new proxy for this next request to not cause an anomalous
            #      request. This way their server sees our ip address as continuously having the
            #      same cookies and not have a request mid-session with no cookies
            self.get('http://' + cookie_domain)

        cookie_added = self.try_add_cookie(cookie)

        # If we fail adding the cookie, retry with a more permissive domain
        if not cookie_added:
            cookie['domain'] = tldextract.extract(cookie['domain']).registered_domain
            cookie_added = self.try_add_cookie(cookie)
            if not cookie_added:
                raise WebDriverException("Couldn't add the following cookie to the webdriver: {}".format(cookie))

    def is_cookie_in_driver(self, cookie):
        """We check that the cookie is correctly added to the driver

        We only compare name, value and domain, as the rest can produce false negatives.
        We are a bit lenient when comparing domains.
        """
        for driver_cookie in self.get_cookies():
            name_matches = cookie['name'] == driver_cookie['name']
            value_matches = cookie['value'] == driver_cookie['value']
            domain_matches = driver_cookie['domain'] in (cookie['domain'], '.' + cookie['domain'])
            if name_matches and value_matches and domain_matches:
                return True
        return False

    def ensure_element_by_id(self, selector, state="present", timeout=None):
        return self.ensure_element('id', selector, state, timeout)

    def ensure_element_by_name(self, selector, state="present", timeout=None):
        return self.ensure_element('name', selector, state, timeout)

    def ensure_element_by_xpath(self, selector, state="present", timeout=None):
        return self.ensure_element('xpath', selector, state, timeout)

    def ensure_element_by_link_text(self, selector, state="present", timeout=None):
        return self.ensure_element('link_text', selector, state, timeout)

    def ensure_element_by_partial_link_text(self, selector, state="present", timeout=None):
        return self.ensure_element('partial_link_text', selector, state, timeout)

    def ensure_element_by_tag_name(self, selector, state="present", timeout=None):
        return self.ensure_element('tag_name', selector, state, timeout)

    def ensure_element_by_class_name(self, selector, state="present", timeout=None):
        return self.ensure_element('class_name', selector, state, timeout)

    def ensure_element_by_css_selector(self, selector, state="present", timeout=None):
        return self.ensure_element('css_selector', selector, state, timeout)

    def ensure_element(self, locator, selector, state="present", timeout=None):
        """This method allows us to wait till an element appears or disappears in the browser

        The webdriver runs in parallel with our scripts, so we must wait for it everytime it
        runs javascript. Selenium automatically waits till a page loads when GETing it,
        but it doesn't do this when it runs javascript and makes AJAX requests.
        So we must explicitly wait in that case.

        The 'locator' argument defines what strategy we use to search for the element.

        The 'state' argument allows us to chose between waiting for the element to be visible,
        clickable, present, or invisible. Presence is more inclusive, but sometimes we want to
        know if the element is visible. Careful, its not always intuitive what Selenium considers
        to be a visible element. We can also wait for it to be clickable, although this method
        is a bit buggy in selenium, an element can be 'clickable' according to selenium and
        still fail when we try to click it.

        More info at: http://selenium-python.readthedocs.io/waits.html
        """
        locators = {'id': By.ID,
                    'name': By.NAME,
                    'xpath': By.XPATH,
                    'link_text': By.LINK_TEXT,
                    'partial_link_text': By.PARTIAL_LINK_TEXT,
                    'tag_name': By.TAG_NAME,
                    'class_name': By.CLASS_NAME,
                    'css_selector': By.CSS_SELECTOR}
        locator = locators[locator]
        if not timeout:
            timeout = self.default_timeout

        if state == 'visible':
            element = WebDriverWait(self, timeout).until(
                expected_conditions.visibility_of_element_located((locator, selector))
            )
        elif state == 'clickable':
            element = WebDriverWait(self, timeout).until(
                expected_conditions.element_to_be_clickable((locator, selector))
            )
        elif state == 'present':
            element = WebDriverWait(self, timeout).until(
                expected_conditions.presence_of_element_located((locator, selector))
            )
        elif state == 'invisible':
            WebDriverWait(self, timeout).until(
                expected_conditions.invisibility_of_element_located((locator, selector))
            )
            element = None
        else:
            raise ValueError(
                "The 'state' argument must be 'visible', 'clickable', 'present' "
                "or 'invisible', not '{}'".format(state)
            )

        # We add this method to our element to provide a more robust click. Chromedriver
        # sometimes needs some time before it can click an item, specially if it needs to
        # scroll into it first. This method ensures clicks don't fail because of this.
        if element:
            element.ensure_click = functools.partial(_ensure_click, element)
        return element

    @property
    def selector(self):
        """Returns the current state of the browser in a Selector

        We re-parse the site on each xpath, css, re call because we are running a web browser
        and the site may change between calls"""
        return Selector(text=self.page_source)

    def xpath(self, *args, **kwargs):
        return self.selector.xpath(*args, **kwargs)

    def css(self, *args, **kwargs):
        return self.selector.css(*args, **kwargs)

    def re(self, *args, **kwargs):
        return self.selector.re(*args, **kwargs)

    def re_first(self, *args, **kwargs):
        return self.selector.re_first(*args, **kwargs)


def _ensure_click(self):
    """Ensures a click gets made, because Selenium can be a bit buggy about clicks

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
    script = ("var viewPortHeight = Math.max("
              "document.documentElement.clientHeight, window.innerHeight || 0);"
              "var elementTop = arguments[0].getBoundingClientRect().top;"
              "window.scrollBy(0, elementTop-(viewPortHeight/2));")
    self.parent.execute_script(script, self)  # parent = the webdriver

    for _ in range(10):
        try:
            self.click()
            return
        except WebDriverException as e:
            exception_message = str(e)
            time.sleep(0.2)
    raise WebDriverException(
        "Couldn't click item after trying 10 times, got error message: \n{}".format(
            exception_message
        )
    )

import requests
import time
import tldextract

from functools import partial
from parsel.selector import Selector
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class Session(requests.Session):
    """Class that adds a Selenium Webdriver and helper methods to a  Requests Session

    This session class is a normal Requests Session that has the ability to switch back
    and forth between this session and a webdriver, allowing us to run js when needed.

    Cookie transfer is done with the 'switch' methods.

    Header and proxy transfer is done only one time when the driver process starts.

    Some usefull helper methods and object wrappings have been added.
    """

    def __init__(self, webdriver_path='./phantomjs', default_timeout=5, browser='phantomjs'):
        super(Session, self).__init__()
        self.webdriver_path = webdriver_path
        self.default_timeout = default_timeout
        self.browser = browser
        self._driver = None
        self._last_requests_url = None

    @property
    def driver(self):
        if self._driver is None:
            if self.browser == 'phantomjs':
                self._driver = self._start_phantomjs_browser()
            elif self.browser == 'chrome':
                self._driver = self._start_chrome_browser()
            else:
                raise AttributeError(
                    'Browser must be chrome or phantomjs, not: "{}"'.format(self.browser)
                )

        return self._driver

    def _start_phantomjs_browser(self):
        # Add headers to driver
        for key, value in self.headers.items():
            # Manually setting Accept-Encoding to anything breaks it for some reason, so we skip it
            if key == 'Accept-Encoding': continue

            webdriver.DesiredCapabilities.PHANTOMJS[
                'phantomjs.page.customHeaders.{}'.format(key)] = value

        # Set browser options
        service_args = ['--load-images=no', '--disk-cache=true']

        # Add proxies to driver
        if self.proxies:
            session_proxy = self.proxies['https'] or self.proxies['http']
            proxy_user_and_pass = session_proxy.split('@')[0].split('://')[1]
            proxy_ip_address = session_proxy.split('@')[1]
            service_args.append('--proxy=' + proxy_ip_address)
            service_args.append('--proxy-auth=' + proxy_user_and_pass)

        # Create driver process
        return RequestiumPhantomJS(executable_path=self.webdriver_path,
                                   service_log_path="/tmp/ghostdriver.log",
                                   service_args=service_args,
                                   default_timeout=self.default_timeout)

    def _start_chrome_browser(self):
        # TODO transfer headers, and authenticated proxies: not sure how to do it in chrome yet
        chrome_options = webdriver.chrome.options.Options()

        # I suspect the infobar at the top of the browser saying "Chrome is being controlled by an
        # automated software" sometimes hides elements from being clickable. So I disable it.
        chrome_options.add_argument('disable-infobars')

        # Create driver process
        return RequestiumChrome(self.webdriver_path,
                                chrome_options=chrome_options,
                                default_timeout=self.default_timeout)

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
            self.driver.ensure_add_cookie({'name': c.name, 'value': c.value, 'path': c.path,
                                           'expiry': c.expires, 'domain': c.domain})

    def transfer_driver_cookies_to_session(self):
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


class RequestiumResponse(object):
    """Adds xpath, css, and regex methods to a normal requests response object"""

    def __init__(self, response):
        self.__class__ = type(response.__class__.__name__,
                              (self.__class__, response.__class__),
                              response.__dict__)
        self._response = response
        self._selector = None

    @property
    def selector(self):
        if self._selector is None:
            self._selector = Selector(text=self._response.text)
        return self._selector

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

    This is a temporary solution.

    When Chrome headless is finally stable, and we therefore stop using Phantomjs,
    it will make sense to stop having this as a mixin and just add these methods to
    the RequestiumChrome class, as it will be our only driver class.

    (We plan to stop supporting Phantomjs because the developer stated he wont be
    mantaining the project any longer)
    """

    def __init__(self, *args, **kwargs):
        self.default_timeout = kwargs['default_timeout']
        del kwargs['default_timeout']
        super(DriverMixin, self).__init__(*args, **kwargs)

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
            #      request. This way their server sees our ip address as continously having the
            #      same cookies and not have a request mid-session with no cookies
            self.get('http://' + cookie_domain)

        # Fixes phantomjs bug, all domains must start with a period
        if self.name == "phantomjs": cookie['domain'] = '.' + cookie['domain']
        self.add_cookie(cookie)

        # If we fail adding the cookie, retry with a more permissive domain
        if not self.is_cookie_in_driver(cookie):
            cookie['domain'] = tldextract.extract(cookie['domain']).registered_domain
            self.add_cookie(cookie)
            if not self.is_cookie_in_driver(cookie):
                raise WebDriverException(
                    "Couldn't add the following cookie to the webdriver\n{}\n".format(cookie)
                )

    def is_cookie_in_driver(self, cookie):
        """We check that the cookie is correctly added to the driver

        We only compare name, value and domain, as the rest can produce false negatives.
        We are a bit lenient when comparing domains.
        """
        for driver_cookie in self.get_cookies():
            if (cookie['name'] == driver_cookie['name'] and
                cookie['value'] == driver_cookie['value'] and
                (cookie['domain'] == driver_cookie['domain'] or
                 '.' + cookie['domain'] == driver_cookie['domain'])):
                return True
        return False

    def ensure_element_by_xpath(self, selector, criterium="presence", timeout=None):
        """This method allows us to wait till an element is loaded in selenium

        This method is added to the driver object. And its more robust than any of Selenium's
        default options for waiting for elements.

        Selenium runs in parallel with our scripts, so we must wait for it everytime it
        runs javascript. Selenium automatically makes our python scripts when its GETing
        a new webpage, but it doesnt do this when it runs javascript and makes AJAX requests.
        So we must explicitly wait in this case.

        The 'criterium' parameter allows us to chose between the visibility and presence of
        the item in the webpage. Presence is more inclusive, but sometimes we want to know if
        the element is visible. Careful, its not always intuitive what Selenium considers to be
        a visible element.

        This is a barebones implementation, which only supports xpath. It could be usefull to
        add more filters in the future, a comprehensive list of the possible filters can be
        found here: http://selenium-python.readthedocs.io/waits.html

        This function returns the element its waiting for, so it could actually replace
        the default selenium method 'find_element_by_xpath'. I am not doing it for the time being
        as it could cause confusion and have some adverse effects I may not not be aware of,
        but its worth considering doing it when this whole library is more stable and we have a
        better defined api.

        This function also scrolls the element into view before returning it, so we can ensure that
        the element is clickable before returning it.
        """
        type = By.XPATH
        if not timeout: timeout = self.default_timeout

        if criterium == 'visibility':
            element = WebDriverWait(self, timeout).until(
                EC.visibility_of_element_located((type, selector))
            )
        elif criterium == 'clickable':
            element = WebDriverWait(self, timeout).until(
                EC.element_to_be_clickable((type, selector))
            )
        elif criterium == 'presence':
            element = WebDriverWait(self, timeout).until(
                EC.presence_of_element_located((type, selector))
            )
        else:
            raise ValueError(
                "The 'criterium' argument must be 'visibility', 'clickable' "
                "or 'presence', not '{}'".format(criterium)
            )

        # We add this method to our element to provide a more robust click. Chromedriver
        # sometimes needs some time before it can click an item, specially if it needs to
        # scroll into it first. This method ensures clicks don't fail because of this.
        element.ensure_click = partial(_ensure_click, element)
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
    """Ensures a click gets made, cause Selenium can be a bit buggy about clicks

    This method gets added to the selenium elemenent returned in '__ensure_element_by_xpath'.
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
    self.parent.execute_script(script, self)  # parent = the webdriber

    for _ in range(10):
        try:
            self.click()
            return
        except WebDriverException as e:
            time.sleep(0.2)
    raise WebDriverException(
        "Couldn't click item after trying 10 times, got error message: \n{}".format(e.message)
    )


class RequestiumPhantomJS(DriverMixin, webdriver.PhantomJS):
    pass


class RequestiumChrome(DriverMixin, webdriver.Chrome):
    pass

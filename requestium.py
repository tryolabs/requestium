import requests
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from parsel.selector import Selector
import tldextract


class Session(requests.Session):
    """Class that mixes Requests' Sessions, Selenium Webdriver, plus helper methods

    This session class is a normal Requests Session that has the ability to switch back
    and forth between this session and a webdriver, allowing us to run js when needed.

    Cookie transfer is done with the 'switch' methods.

    Header and proxy transfer is done only one time when the driver process starts.

    Some usefull helper methods and object wrappings have been added.
    """
    _driver = None
    _last_requests_url = None

    def __init__(self, webdriver_path='./local_phantomjs', default_wait_timeout=5):
        super(Session, self).__init__()
        self.webdriver_path = webdriver_path
        self.default_wait_timeout = default_wait_timeout

    @property
    def driver(self):
        if self._driver is None:
            # Add headers to driver
            for key, value in self.headers.items():
                # Manually setting the encoding to anything breaks it
                if key == 'Accept-Encoding': continue

                webdriver.DesiredCapabilities.PHANTOMJS[
                    'phantomjs.page.customHeaders.{}'.format(key)] = value

            # Set browser options
            service_args = ['--load-images=no', '--disk-cache=true']

            # Add proxies to driver
            if self.proxies:
                session_proxy = self.proxies['https'] or self.proxies['http']
                proxy_user_and_pass = session_proxy.split('@')[0][7:]
                proxy_ip_address = session_proxy.split('@')[1]
                service_args.append('--proxy=' + proxy_ip_address)
                service_args.append('--proxy-auth=' + proxy_user_and_pass)

            # Create driver process
            self._driver = webdriver.PhantomJS(executable_path=self.webdriver_path,
                                               service_log_path="/tmp/ghostdriver.log",
                                               service_args=service_args)

            # Add extra method to driver
            self.driver.wait_for_xpath = self.__wait_for_xpath
        return self._driver

    def update_driver_cookies(self, url=None):
        """Copies the Session's cookies into the webdriver

        You can only transfer cookies to the driver if its current url is the same
        as the cookie's domain. This is a limitation that selenium imposes.
        """

        if url is None:
            url = self._last_requests_url

        # Check if the driver should go to a certain domain before transferring cookies
        # (Selenium and Requests prepend domains with an '.')
        driver_tld = self.get_tld(self.driver.current_url)
        new_request_tld = self.get_tld(url)
        if '.' + new_request_tld in self.cookies.list_domains() and driver_tld != new_request_tld:
            self.driver.get('http://' + self.get_tld(url))
            driver_tld = self.get_tld(self.driver.current_url)
            # assert driver_tld == new_request_tld, "{} != {}".format(driver_tld, new_request_tld)

        # Transfer cookies
        for c in self.cookies:
            self.driver.add_cookie({'name': c.name, 'value': c.value, 'path': c.path,
                                    'expiry': c.expires, 'domain': c.domain})

        self.driver.get(url)

    def switch_to_requests(self):
        for cookie in self.driver.get_cookies():
                self.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

    def get_tld(self, url):
        """Return the top level domain

        If the registered domain could not be extracted, assume that it's simply an IP and
        strip away the protocol prefix and potentially trailing rest after "/" away.
        If it isn't, this fails gracefully for unknown domains, e.g.:
           "http://domain.onion/" -> "domain.onion". If it doesn't look like a valid address
        at all, return the URL unchanged.
        """
        components = tldextract.extract(url)
        if not components.registered_domain:
            try:
                return url.split('://', 1)[1].split(':', 1)[0].split('/', 1)[0]
            except IndexError:
                return url
        return components.registered_domain

    def __wait_for_xpath(self, selector, criterium="presence", timeout=None):
        """This method allows us to wait till an element is loaded in selenium.

        This method is added to the driver object.

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
        """
        type = By.XPATH
        if not timeout: timeout = self.default_wait_timeout

        if criterium == 'visibility':
            return WebDriverWait(self._driver, timeout).until(
                EC.visibility_of_element_located((type, selector))
            )
        else:
            return WebDriverWait(self._driver, timeout).until(
                EC.presence_of_element_located((type, selector))
            )

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
        # self.__dict__ = response.__dict__  # TODO delete?
        self.response = response
        self._selector = None

    @property
    def selector(self):
        if self._selector is None:
            self._selector = Selector(text=self.response.text)
        return self._selector

    def xpath(self, *args, **kwargs):
        return self.selector.xpath(*args, **kwargs)

    def css(self, *args, **kwargs):
        return self.selector.css(*args, **kwargs)

    def re(self, *args, **kwargs):
        return self.selector.re(*args, **kwargs)

import unittest

from requestium import Session, Keys


class ChromeTestCase(unittest.TestCase):
    def setUp(self):
        self.s = Session('chromedriver',
                         browser='chrome',
                         default_timeout=15,
                         webdriver_options={'arguments': ['headless', 'disable-gpu']})

    def test_cookie_transfer_to_requests(self):
        """Tested on http://testing-ground.scraping.pro/login"""

        self.s.driver.get('http://testing-ground.scraping.pro/login')
        self.s.driver.find_element_by_id('usr').send_keys('admin')
        self.s.driver.ensure_element_by_id('pwd').send_keys('12345', Keys.ENTER)
        self.s.driver.ensure_element_by_xpath('//div[@id="case_login"]/h3[@class="success"]')

        self.s.transfer_driver_cookies_to_session()
        response = self.s.get('http://testing-ground.scraping.pro/login?mode=welcome')
        success_message = response.xpath(
            '//div[@id="case_login"]/h3[@class="success"]/text()').extract_first()

        self.assertEqual(
            success_message, 'WELCOME :)', 'Failed to transfer cookies from Selenium to Requests')

    def test_cookie_transfer_to_selenium(self):
        self.s.get('http://testing-ground.scraping.pro/login')
        self.s.cookies.set('tdsess', 'TEST_DRIVE_SESSION', domain='testing-ground.scraping.pro')

        self.s.transfer_session_cookies_to_driver()
        self.s.driver.get('http://testing-ground.scraping.pro/login?mode=welcome')
        success_message = self.s.driver.xpath(
            '//div[@id="case_login"]/h3[@class="success"]/text()').extract_first()

        self.assertEqual(
            success_message, 'WELCOME :)', 'Failed to transfer cookies from Requests to Selenium')

    def tearDown(self):
        self.s.driver.close()


class PhantomjsTestCase(ChromeTestCase):
    def setUp(self):
        self.s = Session('phantomjs',
                         browser='phantomjs',
                         default_timeout=15)


if __name__ == '__main__':
    unittest.main()

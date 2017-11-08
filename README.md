# Requestium

The objective of this project is to help in the development of bots that automatize actions in websites, and who need to dynamically switch between plain http requests and a js-enabled browser during a single session. We do this by adding a [Selenium](https://github.com/SeleniumHQ/selenium) webdriver to a [requests](https://github.com/requests/requests)' Session object.

This new Session object is a drop in replacement of the standard requests Session object, and every new feature is lazily evaluated, so there is no overhead in using this library over just plain requests.

The library also adds several convenience features. The biggest one is integrating [parsel](https://github.com/scrapy/parsel)'s parser into the library. You can seamlessly run xpaths, css or regex anywhere in the library without having to manually parse anything, resulting in much cleaner code. Additionally, it improves the managing of cookies and proxies in Selenium, and has several workarounds for parts of Selenium which are buggy or not super stable.

## Usage
```python
from requestium import Session, Keys

# Currently supports phantomjs, chrome and chrome headless as the webdriver
s = Session(webdriver_path='./chromedriver', default_timeout=15, browser='chrome')

# We don't need to parse the response, it is done automatically when calling xpath, css or re
title = s.get('http://samplesite.com').xpath('//title/text()').extract_first(default='Sample Title')

# Regex require much less boilerplate
response = s.get('http://samplesite.com/sample_path')
list_of_two_digit_numbers = response.re(r'\d\d')  # Extracts all matches as a list
print "Site ID: {}".format(response.re_first(r'ID_\d\w\d'), default='1A1')  # Extracts the first match

# We can use all the regular requests' Session methods
s.post('http://www.samplesite.com/sample', data={'field1': 'data1'})

# And we can switch to using the Selenium webdriver to run any js code
s.transfer_session_cookies_to_driver()  # We can mantain the session if needed
s.driver.get('http://www.samplesite.com/sample/process')

# The driver object is a Selenium webdriver object, so we use any of the normal selenium
# methods plus new ones we added.
s.driver.find_element_by_xpath("//input[@class='user_name']").send_keys('James Bond', Keys.ENTER)
s.driver.find_element_by_xpath("//div[@uniqueattribute='important_button']").click()

# We also add parsel's xpath, css, and re to the Selenium driver object
if s.driver.re(r'ID_\d\w\d some_pattern'):
    print 'Found it!'

# And finally we can switch back to using requests
s.transfer_driver_cookies_to_session()
s.post('http://www.samplesite.com/sample2', data={'key1': 'value1'})
```

## Considerations
New features are lazily evaluated, meaning:
- The Selenium webdriver process is only started if we call the driver object. So if we don't need to use the webdriver, we could use the library with no overhead. Very useful if you just want to use the library for its addition of parsel.
- Parsing of the responses is only done if we call the `xpath`, `css`, or `re` methods of the response. So again there is no overhead if we don't need to use this feature.

A byproduct of this feature is that The Selenium webdriver could be used just to ease in the development of regular requests code: You can start writing your script using just the requests' session, and at the last step of the script (the one you are currently working on) transfer the session to the Chrome webdriver. This way, a Chrome process starts in your machine, and acts as a real time "visor" for the last step of your code. You can see in what state your session is currently in, inspect it with Chrome's excellent inspect tools, and decide what's the next step your session object should take. Very useful to try code in an ipython interpreter and see how the site reacts in real time.

The Chrome driver doesn't support automatic transfer of headers and proxies from the Session to the Webdriver at the moment. The phantomjs driver does though.

## Selenium workarounds
We add several 'ensure' methods to the driver object, as Selenium is known to be very finicky about selecting elements and cookie handling.

### Wait for element
The `ensure_element_by_` methods waits for the element to be loaded in the browser and returns it as soon as it loads. Named after Selenium's `find_element_by_` methods (which raise an exception if they can't find the element). By default we can wait for the element to be present, but we can also wait for it to be clickable or visible. Very useful for single page web apps. We usually end up completely replacing our `find_element_by_` calls with `ensure_element_by_` calls as they are more flexible.

Elements we get using this method have the `ensure_click` method which makes the click less prone to failure. This helps us get through a lot of the problems with Selenium clicking.


```python
s.driver.ensure_element_by_xpath("//li[@class='b1']", criterium='clickable', timeout=5).ensure_click()

# === We also added these methods named in accordance to Selenium's api design ===
# ensure_element_by_css
# ensure_element_by_id
# ensure_element_by_class
# ensure_element_by_link_text
# ensure_element_by_partial_link_text
# ensure_element_by_name
# ensure_element_by_tag_name

# === Though you can also call ensure_element directly ===
s.driver.ensure_element("xpath", "//li[@class='b1']", criterium='clickable', timeout=5)
```

### Wait for element to disappear
The `wait_element_disappears_by_` methods waits for the element to be loaded in the browser and then waits until it disappears. It looks for an element in first place, using two timeouts: one for locating the element, and other one to wait until it disappears (often the former will be shorter than the latter). Very useful each time you have to wait for a loading gif to go away.

The criterium to check if item disappeared will be `visibility`. A `TimeoutException` will rise if the element is located and it does not disappear after waiting for `disappear_timeout`

```python
s.driver.wait_element_disappears_by_xpath("//img[@class='loading']",
                                          criterium='visibility',
                                          appear_timeout=2,
                                          disappear_timeout=10)

# === We also added these methods named in accordance to Selenium's api design ===
# wait_element_disappears_by_css
# wait_element_disappears_by_id
# wait_element_disappears_by_class
# wait_element_disappears_by_link_text
# wait_element_disappears_by_partial_link_text
# wait_element_disappears_by_name
# wait_element_disappears_by_tag_name

# === You can also call wait_element_disappears directly ===
s.driver.wait_element_disappears("xpath",
                                 "//img[@class='loading']",
                                 criterium='visibility',
                                 appear_timeout=2,
                                 disappear_timeout=10)
```

### Add cookie
The `ensure_add_cookie` method makes adding cookies much more robust. Selenium needs the browser to be at the cookie's domain before being able to add the cookie, this method offers several workarounds for this. If the browser is not in the cookies domain, it GETs the domain before adding the cookie. It also allows you to override the domain before adding it, and avoid making this GET. The domain can be overridden to `''`, this sets the cookie's domain to whatever domain the driver is currently in.

If it can't add the cookie it tries to add it with a less restrictive domain (Eg.: home.site.com -> site.com) before failing.

```python
cookie = {"domain": "www.site.com",
          "secure": false,
          "value": "sd2451dgd13",
          "expiry": 1516824855.759154,
          "path": "/",
          "httpOnly": true,
          "name": "sessionid"}
s.driver.ensure_add_cookie(cookie, override_domain='')
```

## Installation and Hello world example

### Installation
```bash
pip install requestium
```
Then download your preferred Selenium webdriver if you plan to use the Selenium part of requestium: [chromedriver](https://sites.google.com/a/chromium.org/chromedriver/) or [phantomjs](http://phantomjs.org)

### Hello world example
Just a silly working example of a script that runs on reddit. We'll then show how it compares to using requests + Selenium + lxml instead of requestium.
```python
from requestium import Session, Keys

# If you want requestium to type your username in the browser for you, write it in here
reddit_user_name = ''

s = Session('./chromedriver', browser='chrome', default_timeout=15)
s.driver.get('http://reddit.com')
s.driver.find_element_by_xpath("//a[@href='https://www.reddit.com/login']").click()

print('Waiting for elements to load...')
s.driver.ensure_element_by_class("desktop-onboarding-sign-up__form-toggler").click()

if reddit_user_name:
    s.driver.ensure_element_by_id('user_login').send_keys(reddit_user_name)
    s.driver.ensure_element_by_id('passwd_login').send_keys(Keys.BACKSPACE)
print 'Please log-in in the chrome browser'

s.driver.wait_element_disappears_by_class(
    "desktop-onboarding__title", appear_timeout=3, disappear_timeout=60)
print 'Thanks!'

if not reddit_user_name:
    reddit_user_name = s.driver.xpath("//span[@class='user']//text()").extract_first()

if reddit_user_name:
    s.transfer_driver_cookies_to_session()
    response = s.get("https://www.reddit.com/user/{}/".format(reddit_user_name))
    cmnt_karma = response.xpath("//span[@class='karma comment-karma']//text()").extract_first()
    reddit_golds_given = response.re_first(r"(\d+) gildings given out")
    print "Comment karma: {}".format(cmnt_karma)
    print "Reddit golds given: {}".format(reddit_golds_given)
else:
    print "Couldn't get user name"
```

### Comparison with requests + Selenium + lxml
Same as the previous script but without using requestium. Most of requestium's robustness improvements such as the `ensure_click` method and the better adding of cookies to Selenium are not shown though.
```python
import re
from lxml import etree
from requests import Session
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# If you want requestium to type your username in the browser for you, write it in here
reddit_user_name = ''

driver = webdriver.Chrome('./chromedriver')
driver.get('http://reddit.com')
driver.find_element_by_xpath("//a[@href='https://www.reddit.com/login']").click()

print('Waiting for elements to load...')
WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.CLASS_NAME, "desktop-onboarding-sign-up__form-toggler"))
).click()

if reddit_user_name:
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, 'user_login'))
    ).send_keys(reddit_user_name)
    driver.find_element_by_id('passwd_login').send_keys(Keys.BACKSPACE)
print 'Please log-in in the chrome browser'

try:
    WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.CLASS_NAME, "desktop-onboarding__title"))
    )
except TimeoutException:
    pass
WebDriverWait(driver, 60).until(
    EC.invisibility_of_element_located((By.CLASS_NAME, "desktop-onboarding__title"))
)
print 'Thanks!'

if not reddit_user_name:
    tree = etree.HTML(driver.page_source)
    try:
        reddit_user_name = tree.xpath("//span[@class='user']//text()")[0]
    except IndexError:
        reddit_user_name = None

if reddit_user_name:
    s = Session()
    # Reddit will think we are a bot if we have the wrong user agent
    selenium_user_agent = driver.execute_script("return navigator.userAgent;")
    s.headers.update({"user-agent": selenium_user_agent})
    for cookie in driver.get_cookies():
        s.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
    response = s.get("https://www.reddit.com/user/{}/".format(reddit_user_name))
    try:
        cmnt_karma = etree.HTML(response.content).xpath(
            "//span[@class='karma comment-karma']//text()")[0]
    except IndexError:
        cmnt_karma = None
    match = re.search(r"(\d+) gildings given out", response.content)
    try:
        reddit_golds_given = match.group(1)
    except AttributeError:
        reddit_golds_given = None
    print "Comment karma: {}".format(cmnt_karma)
    print "Reddit golds given: {}".format(reddit_golds_given)
else:
    print "Couldn't get user name"
```


## Selenium-Requests
This project intends to be a drop in replacement of requests' Session object, with added functionality. If your use case is a drop in replacement for a Selenium webdriver, but that also has some of requests' functionality, [Selenium-Requests](https://github.com/cryzed/Selenium-Requests) does just that.

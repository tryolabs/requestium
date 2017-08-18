# Requestium

The objective of this project is to help in the development of bots that automatize actions in websites, and who need to dynamically switch between plain http requests and a js-enabled browser in a single session. We do this by adding a [Selenium webdriver](https://github.com/SeleniumHQ/selenium) webdriver to a [request](https://github.com/requests/requests)'s Session object. This new Session object is a drop in replacement of the standard requests Session object.

We also integrate [parsel](https://github.com/scrapy/parsel)'s parser into the library as its very useful and concise.

## Usage
```python
from requestium import Session, Keys
# from requests import Session  # The new Session object is backwards compatible with the old one.

# Currently supports phantomjs and chrome as the webdriver
s = Session(webdriver_path='./chromedriver', default_timeout=15, browser='chrome')

# We don't need to parse the response, it is done automatically when calling xpath, css or re
title = s.get('http://samplesite.com').xpath('//title/text()').extract_first(default='Sample Title')

# Regex require much less boilerplate
response = s.get('http://samplesite.com/sample_path')
list_of_two_digit_numbers = response.re(r'\d\d')  # Extracts all matches as a list
print "Site ID: {}".format(response.re_first(r'ID_\d\w\d'), default='1A1')  # Extracts the first match

# We can use all the normal Session methods
s.post('http://www.samplesite.com/sample', data={'field1': 'data1'})

# And we can switch to using the Selenium webdriver to run any js code
s.update_driver_cookies()  # We can mantain the session if needed
s.driver.get('http://www.samplesite.com/sample/process')
s.driver.find_element_by_xpath("//input[@class='user_name']").send_keys('James Bond', Keys.ENTER)
s.driver.find_element_by_xpath("//div[@uniqueattribute='important_button']").click()

# We also add parsel's xpath, css, and re to the driver object
if s.driver.re(r'ID_\d\w\d some_pattern'):
    print 'Found it!'

# And finally we can switch back to using requests
s.update_session_cookies()
s.post('http://www.samplesite.com/sample2', data={'key1': 'value1'})
```

## Considerations
Most things are lazily evaluated, meaning:
- The webdriver process is only started if we call the driver object. So if we don't need to use the webdriver, we could use the library with no overhead.
- Parsing of the responses is only done if we call the `xpath`, `css`, or `re` methods of the response. So again there is no overhead if we dont need to use this feature.

We can use our custom Session class just for development, maybe to dynamically watch the last step of the session in a chrome browser running without the `--headless` flag, and remove this last step after development is done. After this we could just remove import the Session class as `from requests import Session` and just deploy to production without using requestium.

This project intends to be a drop in replacement of requests' Session object, with added functionality. If your use case is a drop in replacement for a Selenium webdriver, but that also has some of requests' functionality, [Selenium-Requests](https://github.com/cryzed/Selenium-Requests) does just that.

The chrome driver doesn't support automatic transfer of headers and proxies from the Session to the Webdriver at the moment. The phantomjs driver does though.

## Selenium workarounds
We add several 'ensure' methods to the driver object, as Selenium is known to be very finicky about cookie handling and selecting elements.

### Wait for element
The `ensure_element_by_` methods waits for the element to be loaded in the browser and returns it as soon as it is. Named after Selenium's `find_element_by_` methods. By default we can wait for the element to be present, but we can also wait for it to be clickable or visible. Very useful for single page web apps.

Elements we get using this method have the `ensure_click` method which makes the click less prone to failure. This helps us get through a lot of the problems with Selenium clicking.

`timeout` defaults to the `default_timeout` set when creating the Session object.

```python
s.driver.ensure_element_by_xpath("//li[@class='b1']", criterium='clickable', timeout=5).ensure_click()

# === Also supported ===
# ensure_element_by_css
# ensure_element_by_id
# ensure_element_by_class
# ensure_element_by_link_text
# ensure_element_by_partial_link_text
# ensure_element_by_name
# ensure_element_by_tag_name

# === You can also call ensure_element directly ===
s.driver.ensure_element("xpath", "//li[@class='b1']", criterium='clickable', timeout=5)
```

### Add cookie
The `ensure_add_cookie` method makes adding cookies much more robust. Selenium needs the browser to be at the cookie's domain before being able to add the cookie, this method offers several workarounds for this. If the browser is not in the cookies domain, it GETs the domain before adding the cookie. It also allows you to override the domain before adding it, and avoid making this GET. The domain can be overridden to `''` to give the cookie whatever domain the driver is currently in.

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

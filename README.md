# Requestium

The objective of this project is to help in the development of bots that automatize actions in websites, and who need to dynamically switch between plain http requests and a js-enabled browser in a single session. We do this by adding a [Selenium webdriver](https://github.com/SeleniumHQ/selenium) and [parsel](https://github.com/scrapy/parsel)'s parser to a [request](https://github.com/requests/requests)'s Session object. This new session object is a drop in replacement of the standard requests session object.

## Usage
```python
from requestium import Session, Keys
# from requests import Session  # We replace this statement

s = Session()

# We don't need to parse the response, it is done automatically
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

# And then switch back to using requests
s.update_session_cookies()
s.post('http://www.samplesite.com/sample2', data={'field2': 'data2'})
```

## Considerations
Most things are lazily evaluated, meaning:
- The webdriver process is only started if we call the driver object. So if we dont need to use the webdriver, we could use the library with no overhead.
- Parsing of the responses is only done if we call the `xpath`, `css`, or `re` methods of the response. So again there is no overhead if we dont need to use this features.

We can use our custom Session class just for development, maybe to dynamically watch the last step of the session in a chrome browser running without the `--headless` flag, and remove this last step after development is done. After this we could just remove import the Session class as `from requests import Session` and just deploy to production without using requestium.

This project intends to be a drop in replacement of requests session object, with added functionality. If your use case is a drop in replacement for a Selenium webdriver, but that also has some of requests' functionality, [Selenium-Requests](https://github.com/cryzed/Selenium-Requests) does just that.

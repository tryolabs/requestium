# Requestium

The objective of this project is to help in the development of bots that automatize actions in websites, and who need to dynamically switch between plain http requests and a js-enabled browser in a single session. We do this by adding a [Selenium webdriver](https://github.com/SeleniumHQ/selenium) webdriver to a [request](https://github.com/requests/requests)'s Session object. This new Session object is a drop in replacement of the standard requests Session object.

We also integrate [parsel](https://github.com/scrapy/parsel)'s parser into the library as its very useful and concise.

## Usage
```python
# from requests import Session  # The new Session object is backwards compatible with the old one.
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
s.driver.find_element_by_xpath("//input[@class='user_name']").send_keys('James Bond', Keys.ENTER)
s.driver.find_element_by_xpath("//div[@uniqueattribute='important_button']").click()

# We also add parsel's xpath, css, and re to the driver object
if s.driver.re(r'ID_\d\w\d some_pattern'):
    print 'Found it!'

# And finally we can switch back to using requests
s.transfer_driver_cookies_to_session()
s.post('http://www.samplesite.com/sample2', data={'key1': 'value1'})
```

## Considerations
Most things are lazily evaluated, meaning:
- The webdriver process is only started if we call the driver object. So if we don't need to use the webdriver, we could use the library with no overhead.
- Parsing of the responses is only done if we call the `xpath`, `css`, or `re` methods of the response. So again there is no overhead if we dont need to use this feature.

The selenium webdriver could be used just to ease in development: You can start writing your script using just the regular requests' session, and on the last step of the script (the one you are currently working on) transfer the session to a chrome webdriver. This way, the chrome webdriver acts as a 'visor' for the last step of your code. You can see in what state your session is currently in, inspect it with Chrome's excellent inspect tools, and decide what's the next step your session object should make.

The chrome driver doesn't support automatic transfer of headers and proxies from the Session to the Webdriver at the moment. The phantomjs driver does though.

## Using Chrome Driver with Selenium's authenticated proxies and custom headers workarounds
Right now there is no way to add headers or authenticated proxies with `Chrome Driver`, but we implemented a workaround using two Chrome extensions, [ModHeader](https://chrome.google.com/webstore/detail/modheader/idgpnmonknjnojddfkpgkljpfnnfcklj) to transfer the headers from the [requests](https://github.com/requests/requests) session to [Selenium webdriver](https://github.com/SeleniumHQ/selenium), and [Proxy Auto Auth](https://chrome.google.com/webstore/detail/proxy-auto-auth/ggmdpepbjljkkkdaklfihhngmmgmpggp) to autenticate the proxy session if this is necessary. To obtain the binary files neccesary to use this functionalities can be obtained with:
- [CRX Extractor](http://crxextractor.com/)
- [Get CRX](https://chrome.google.com/webstore/detail/get-crx/dijpllakibenlejkbajahncialkbdkjc)

The way of setting the path to the `.crx` files is:

```python
# Import requestium Session object as before
from requestium import Session, Keys

# Set the args  mod_header_path, proxy_auto_auth_path or both depending on the functionallity you need.
# Their default values are './ModHeader.crx' and './ProxyAutoAuth.crx' respectively, so naming the binaries that way and 
# locating them in the root directory of your project will get them automatically.

s = Session(
	webdriver_path='./chromedriver', browser='chrome'
	mod_header_path=<ModHeader.crx path>, proxy_auto_auth_path=<ProxyAutoAuth.crx path>)
```

When this is done, requestium will automatically transfer request's session headers and proxy to Selenium's driver when Session.driver is called.

Example:

```pyhton
s.get(<some url>)

# Set custom header
s.headers.update({'header_key': 'value'})
s.driver.get(<some other url>) # Request is made from Chrome Driver with `{'header_key': 'value'}` header

# Set proxy in requests
s.proxies.update({"http": 'http://username:password@proxy_url:proxy_port'}) # or
s.proxies.update({"https": 'https://username:password@proxy_url:proxy_port'}) 

s.driver.get(<some url>) # Request is made from Chrome Driver using authenticated proxy

```

Also we included the arg `headless` whose default value is True, but can be passed as False when creating the Session oject to be able to see the driver state and use the 
Chrome tools to inspect the components.

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

### Wait for element to disappear
The `wait_element_disappears_by_` methods waits for the element to be loaded in the browser and then waits until it disappears. It looks for an element in first place, using two timeouts: one for locating the element, and other one to wait until it disappears (often the former will be shorter than the latter). Very useful each time you have to wait for a loading gif to go away.

Many times the element will disappear before being able to look for it, so that case is handled here. The criterium to check if item disappeared will be `visibility`. A `TimeoutException` will rise if the element is located and it does not disappear after waiting for `disappear_timeout`

`appear_timeout` and `disappear_timeout` default to the `default_timeout` set when creating the Session object.

```python
s.driver.wait_element_disappears_by_xpath("//img[@class='loading']", criterium='visibility', appear_timeout=2, disappear_timeout=10)

# === Also supported ===
# wait_element_disappears_by_css
# wait_element_disappears_by_id
# wait_element_disappears_by_class
# wait_element_disappears_by_link_text
# wait_element_disappears_by_partial_link_text
# wait_element_disappears_by_name
# wait_element_disappears_by_tag_name

# === You can also call wait_element_disappears directly ===
s.driver.wait_element_disappears("xpath", "//img[@class='loading']", criterium='visibility', appear_timeout=2, disappear_timeout=10)
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

## Selenium-Requests
This project intends to be a drop in replacement of requests' Session object, with added functionality. If your use case is a drop in replacement for a Selenium webdriver, but that also has some of requests' functionality, [Selenium-Requests](https://github.com/cryzed/Selenium-Requests) does just that.


## Limitations

As chormedriver doesn't allow to set authenticated proxies or customize the request headers, the extensions ModHeader and Proxy Auto Auth were added in requestium. The problem is that extensions aren't supported (and there aren't going to be supported) in headless mode. After discovering this, the js code of the extensions was revised to see if it was possible to implement it's functions directly with the webdriver.Chrome driver. 
As the extensions uses chrom.webRequest, that wasn't viable as that is't available on chromedriver, so the options are to use headless mode without authenticated proxy and unable to set custom headers, or use it with the browser (quite heavy for the lambdas).

## Next steps

If webRequest is added to the chromedriver it could be possible to implement the extensions functions excecuting their js script directly in the driver instance.

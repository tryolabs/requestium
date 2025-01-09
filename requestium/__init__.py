"""Requestium is a Python library that merges the power of Requests, Selenium, and Parsel into a single integrated tool for automatizing web actions."""

from selenium.common import exceptions  # noqa: F401
from selenium.webdriver.common.by import By  # noqa: F401
from selenium.webdriver.common.keys import Keys  # noqa: F401
from selenium.webdriver.support.ui import Select  # noqa: F401

from .requestium_session import Session  # noqa: F401

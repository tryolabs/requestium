from __future__ import annotations

import requests
from parsel.selector import Selector, SelectorList
from requests import Response


class RequestiumResponse(requests.Response):
    """Adds xpath, css, and regex methods to a normal requests response object."""

    def __init__(self, response: Response) -> None:
        super().__init__()
        self.__class__ = type(response.__class__.__name__, (self.__class__, response.__class__), response.__dict__)

    @property
    def selector(self) -> Selector:
        """
        Returns the response text in a Selector.

        We re-parse the text on each xpath, css, re call in case the encoding has changed.
        """
        return Selector(text=self.text)

    def xpath(self, *args, **kwargs) -> SelectorList[Selector]:
        return self.selector.xpath(*args, **kwargs)

    def css(self, *args, **kwargs) -> SelectorList[Selector]:
        return self.selector.css(*args, **kwargs)

    def re(self, *args, **kwargs) -> list[str]:
        return self.selector.re(*args, **kwargs)

    def re_first(self, *args, **kwargs) -> str | None:
        return self.selector.re_first(*args, **kwargs)

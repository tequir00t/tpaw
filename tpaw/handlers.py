"""Provides classes that handle request dispatching."""

from __future__ import print_function, unicode_literals

import time
from functools import wraps
from threading import Lock
from timeit import default_timer as timer
from requests import Session


class DefaultHandler(object):
    """The base handler that provides thread-safe rate limiting enforcement."""

    last_call = {}  # Stores a two-item list: [lock, previous_call_time]
    rl_lock = Lock()  # lock used for adding items to last_call

    @staticmethod
    def rate_limit(function):
        """Return a decorator that enforces API request limit guidelines.

        We are allowed  to make a API  request every api_request_delay
        seconds as specified in  tpaw.ini. Any function decorated with
        this  will be  forced to  delay _rate_delay  seconds from  the
        calling  of  the  last  function decorated  with  this  before
        executing.

        This  decorator must  be applied  to a  DefaultHandler class
        method  or  instance  method   as  it  assumes  `rl_lock`  and
        `last_call` are available.

        """
        @wraps(function)
        def wrapped(cls, _rate_delay, **kwargs):
            cls.rl_lock.acquire()
            lock_last = cls.last_call.setdefault(0, [Lock(), 0])
            with lock_last[0]:  # Obtain the domain specific lock
                cls.rl_lock.release()
                # Sleep if necessary, then perform the request
                now = timer()
                delay = lock_last[1] + _rate_delay - now
                if delay > 0:
                    now += delay
                    time.sleep(delay)
                lock_last[1] = now
                return function(cls, **kwargs)
        return wrapped

    @classmethod
    def evict(cls, urls):  # pylint: disable=W0613
        """Method utilized to evict entries for the given urls.

        :param urls: An iterable containing normalized urls.
        :returns: The number of items removed from the cache.

        By default this method returns False as a cache need not be present.

        """
        return 0

    def __del__(self):
        """Cleanup the HTTP session."""
        if self.http:
            try:
                self.http.close()
            except:  # Never fail  pylint: disable=W0702
                pass

    def __init__(self):
        """Establish the HTTP session."""
        self.http = Session()  # Each instance should have its own session

    def request(self, request, proxies, timeout, **_):
        """Responsible for dispatching the request and returning the result.

        Network level exceptions should be raised and only
        ``requests.Response`` should be returned.

        :param request: A ``requests.PreparedRequest`` object containing all
            the data necessary to perform the request.
        :param proxies: A dictionary of proxy settings to be utilized for the
            request.
        :param timeout: Specifies the maximum time that the actual HTTP request
            can take.

        ``**_`` should be added to the method call to ignore the extra
        arguments intended for the cache handler.

        """
        return self.http.send(request, proxies=proxies, timeout=timeout,
                              allow_redirects=False)
DefaultHandler.request = DefaultHandler.rate_limit(
    DefaultHandler.request)

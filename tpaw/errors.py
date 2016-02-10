
"""
Error classes.

Includes two main exceptions: ClientException, when something goes
wrong on our end, and APIExeception for when something goes wrong on the
server side. A number of classes extend these two main exceptions for more
specific exceptions.
"""

from __future__ import print_function, unicode_literals

import inspect
import sys


class TPAWException(Exception):
    """The base TPAW Exception class.

    Ideally, this can be caught to handle any exception from TPAW.
    """


class ClientException(TPAWException):
    """Base exception class for errors that don't involve the remote API."""

    def __init__(self, message=None):
        """Construct a ClientException.

        :param message: The error message to display.

        """
        if not message:
            message = 'Clientside error'
        super(ClientException, self).__init__()
        self.message = message

    def __str__(self):
        """Return the message of the error."""
        return self.message


class LoginRequired(ClientException):
    """Indicates that a logged in session is required.

    This exception is raised on a preemptive basis, whereas NotLoggedIn occurs
    in response to a lack of credentials on a privileged API call.

    """

    def __init__(self, function, message=None):
        """Construct a LoginRequired exception.

        :param function: The function that requires login-based authentication.
        :param message: A custom message to associate with the exception.
            Default: `function` requires a logged in session

        """
        if not message:
            message = '`{0}` requires a logged in session'.format(function)
        super(LoginRequired, self).__init__(message)


class OAuthAppRequired(ClientException):
    """Raised when an OAuth client cannot be initialized.

    This occurs when any one of the OAuth config values are not set.

    """


class HTTPException(TPAWException):
    """Base class for HTTP related exceptions."""

    def __init__(self, _raw, message=None):
        """Construct a HTTPException.

        :params _raw: The internal request library response object. This object
            is mapped to attribute `_raw` whose format may change at any time.

        """
        if not message:
            message = 'HTTP error'
        super(HTTPException, self).__init__()
        self._raw = _raw
        self.message = message

    def __str__(self):
        """Return the message of the error."""
        return self.message


class Forbidden(HTTPException):
    """Raised when the user does not have permission to the entity."""


class NotFound(HTTPException):
    """Raised when the requested entity is not found."""


class OAuthException(TPAWException):
    """Base exception class for OAuth API calls.

    Attribute `message` contains the error message.
    Attribute `url` contains the url that resulted in the error.

    """

    def __init__(self, message, url):
        """Construct a OAuthException.

        :param message: The message associated with the exception.
        :param url: The url that resulted in error.

        """
        super(OAuthException, self).__init__()
        self.message = message
        self.url = url

    def __str__(self):
        """Return the message along with the url."""
        return self.message + " on url {0}".format(self.url)


def _build_error_mapping():
    def predicate(obj):
        """Build error mapping """
        return inspect.isclass(obj) and hasattr(obj, 'ERROR_TYPE')

    tmp = {}
    for _, obj in inspect.getmembers(sys.modules[__name__], predicate):
        tmp[obj.ERROR_TYPE] = obj
    return tmp
ERROR_MAPPING = _build_error_mapping()

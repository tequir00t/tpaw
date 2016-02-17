"""
Toptranslation Python API Wrapper

TPAW, an acronym for "Toptranslation Python API Wrapper", is a python
package that allows simple access to Toptranslation's REST API.

More info can be found at https://developer.toptranslation.com
"""

# standard imports
import json
import os
import sys
import re
from requests import Session
from requests.compat import urljoin
# six imports
import six
from six.moves import html_entities, http_cookiejar
# tpaw imports
from tpaw import errors
from tpaw.handlers import DefaultHandler
from tpaw.settings import CONFIG
from tpaw.internal import _prepare_request
__version__ = '0.0.1'


class Config(object):
    # pylint: disable=line-too-long
    """A class containing the configurations"""

    API_PATHS = {'accept_quote':            'quotes/{identifier}/accept',
                 'add_document':            'orders/{identifier}/documents',
                 'create_cost_center':      'cost_centers',
                 'create_order':            'orders',
                 'document_url':            'documents/{identifier}/download',  # NOQA
                 'download_document':       'documents/{identifier}/download',
                 'get_locales':             'locales',
                 'get_user':                'users/me',
                 'invoice_url':             'invoices/{identifier}/download',  # NOQA
                 'list_cost_centers':       'cost_centers',
                 'list_documents':          'orders/{identifier}/documents',
                 'list_invoices':           'orders/{identifier}/invoices',
                 'list_orders':             'orders',
                 'list_quotes':             'orders/{identifier}/quotes',
                 'quote_url':               'quotes/{identifier}/download',
                 'rate_order':              'orders/{identifier}/ratings',
                 'reference_document_url':  'reference_documents/{identifier}/download',  # NOQA
                 'reject_quote':            'quotes/{identifier}/reject',
                 'request_order':           'orders/{identifier}/request',
                 'show_cost_center':        'cost_centers/{identifier}',
                 'show_order':              'orders/{identifier}',
                 'update_order':            'orders/{identifier}',
                 'upload_document':         'documents',
                 'upload_token':            'upload_tokens',
                }

    @staticmethod
    def ua_string(tpaw_info):
        """Returns the user agent string.

        It contains the TPAW version and platform info.

        """

        return '{0} TPAW/{1} Python/{2}'.format(
            tpaw_info, __version__, sys.version.split()[0])

    def __init__(self, site_name, **kwargs):
        """Initialize TPAW configuration"""
        obj = dict(CONFIG.items(site_name))
        for key, value in kwargs.items():
            obj[key] = value

        self.api_url = 'https://' + obj['api_domain']
        self.api_version = 'v' + obj['api_version']
        self.document_url = 'https://' + obj['document_domain']
        self.api_request_delay = float(obj['api_request_delay'])
        self.cache_timeout = float(obj['cache_timeout'])
        self.log_requests = int(obj['log_requests'])
        self.timeout = float(obj['timeout'])
        self.access_token = obj.get('access_token') or None
        self.http_proxy = (obj.get('http_proxy') or
                           os.getenv('http_prox') or None)
        self.https_proxy = (obj.get('https_proxy') or
                            os.getenv('https_prox') or None)

    def __getitem__(self, key):
        """Return the URL for key."""
        return urljoin(self.api_url, self.api_version + '/' +
                       self.API_PATHS[key])

    def document_store_url(self, key):
        """Returns the DocumentStore URL"""
        return urljoin(self.document_url, self.API_PATHS[key])


class BaseTT(object):
    """A base class that allows access to Toptranslation's API"""
    RETRY_CODES = [502, 503, 504]

    def __init__(self, user_agent, site_name=None,
                 handler=None, **kwargs):
        """Initialize connection with Toptranslation's server

        The user_agent is how your application identifies itself.

        site_name  allows you  to  specify which  reddit  you want  to
        connect to.  The installation  defaults are reddit.com, if you
        only need to connect to  reddit.com then you can safely ignore
        this. If you want to  connect to another reddit, set site_name
        to the name  of that reddit. This must match  with an entry in
        praw.ini. If  site_name is  None, then the  site name  will be
        looked for in the environment  variable REDDIT_SITE.  If it is
        not  found  there,  the  default  site  name  reddit  matching
        reddit.com will be used.

        All additional parameters specified via kwargs will be used to
        initialize the Config object.
        """

        if not user_agent or not isinstance(user_agent, six.string_types):
            raise TypeError('user agent must be a non-empty string')

        self.config = Config(site_name or 'toptranslation', **kwargs)
        self.handler = handler or DefaultHandler()
        self.http = Session()
        self.http.headers['User-Agent'] = self.config.ua_string(user_agent)

        # This `Session` object is only used to store request information that
        # is used to make prepared requests. It _should_ never be used to make
        # a direct request, thus we raise an exception when it is used.

        def _req_error(*_, **__):
            raise errors.ClientException('Do not make direct requests.')
        self.http.request = _req_error

        if self.config.http_proxy or self.config.https_proxy:
            self.http.proxies = {}
            if self.config.http_proxy:
                self.http.proxies['http'] = self.config.http_proxy
            if self.config.https_proxy:
                self.http.proxies['https'] = self.config.https_proxy

    def _request(self, url, params=None, data=None, files=None, auth=None,
                 timeout=None, raw_response=False, retry_on_error=False,
                 method=None):
        """Given a page url and a dict of params, open and return the page.

        :param url: the url to grab content from.
        :param params: a dictionary containing the GET data to put in the url
        :param data: a dictionary containing the extra data to submit
        :param files: a dictionary specifying the files to upload
        :param auth: Add the HTTP authentication headers (see requests)
        :param timeout: Specifies the maximum time that the actual HTTP request
            can take.
        :param raw_response: return the response object rather than the
            response body
        :param retry_on_error: if True retry the request, if it fails, for up
            to 3 attempts
        :returns: either the response body or the response object

        """
        def build_key_items(url, params, data, auth, files, method):
            request = _prepare_request(self, url, params, data, auth, files,
                                       method)
            # Prepare extra arguments
            key_items = []
            for key_value in (params, data, request.cookies, auth):
                if isinstance(key_value, dict):
                    key_items.append(tuple(key_value.items()))
                elif isinstance(key_value, http_cookiejar.CookieJar):
                    key_items.append(tuple(key_value.get_dict().items()))
                else:
                    key_items.append(key_value)
            kwargs = {'_rate_delay': int(self.config.api_request_delay)}

            return (request, key_items, kwargs)

        def decode(match):
            return html_entities.name2codepoint[match.group(1)]

        timeout = self.config.timeout if timeout is None else timeout
        request, key_items, kwargs = build_key_items(url, params, data,
                                                     auth, files, method)
        try:
            response = self.handler.request(
                request=request.prepare(),
                proxies=self.http.proxies,
                timeout=timeout, **kwargs)
            if self.config.log_requests >= 2:
                msg = 'status: {0}\n'.format(response.status_code)
                sys.stderr.write(msg)
            self.http.cookies.update(response.cookies)
            return re.sub('&([^;]+);', decode, response.text)
        except errors.HTTPException as error:
            # pylint: disable=W0212
            if error._raw.status_code not in self.RETRY_CODES:
                raise

    def get_content(self, url, params=None, method=None, root_field='data',
                    **kwargs):
        """Method to return JSON Content"""
        params = params or {}
        data = self.request_json(url, method=method, params=params)
        root = data.get(root_field, data)
        for thing in root:
            yield thing

    def request(self, url, params=None, data=None, retry_on_error=False,
                method=None, files=None):
        """Make a HTTP request and return the response"""
        return self._request(url, params, data, raw_response=True,
                             retry_on_error=retry_on_error, method=method,
                             files=files)

    def request_json(self, url, params=None, data=None, as_objects=True,
                     retry_on_error=False, method=None, files=None):
        """Get the JSON processed from a page"""
        response = self._request(url, params, data, method=method,
                                 files=files, retry_on_error=retry_on_error)
        self._request_url = url

        data = json.loads(response)
        delattr(self, '_request_url')
        return data


class UnauthenticatedTT(BaseTT):
    """This mixin provider the UNauthenticated API access for Toptranslation"""
    def __init__(self, *args, **kwargs):
        """Initialize an Unauthenticated instance"""
        super(UnauthenticatedTT, self).__init__(*args, **kwargs)

    def get_locales(self, *args, **kwargs):
        """You can  retrieve a list  of the current  available locales
        from the Toptranslation API. The  API uses locale codes in ISO
        639 notation.
        """
        url = self.config['get_locales']
        return self.get_content(url, *args, **kwargs)

    def upload_token(self, *args, **kwargs):
        """To  upload  to  the   document  store  requires  an  upload
        token.   You   can   use    this   endpoint   to   create   an
        upload_token. Upload tokens  will expire after a  give time so
        they should only be used  right before the upload takes place.
        """
        url = self.config['upload_token']
        return self.request_json(url, method='POST', *args,
                                 **kwargs)['data']['upload_token']


class AuthenticatedTT(UnauthenticatedTT):
    """This mixin provides the Authenticated API Access for Toptranslation"""
    def __init__(self, *args, **kwargs):
        """Initialize an Authenticated instance"""
        super(AuthenticatedTT, self).__init__(*args, **kwargs)
        self.params = {"access_token": self.config.access_token}

    def upload_token(self, *args, **kwargs):
        """To  upload  to  the   document  store  requires  an  upload
        token.   You   can   use    this   endpoint   to   create   an
        upload_token. Upload tokens  will expire after a  give time so
        they should only be used  right before the upload takes place.
        """
        if self.config.access_token is None:
            return super(AuthenticatedTT, self).upload_token(*args, **kwargs)
        else:
            url = self.config['upload_token']
            data = {"access_token": self.config.access_token}
            return self.request_json(url, data=data, method='POST', *args,
                                     **kwargs)['data']['upload_token']


class OrderMixin(AuthenticatedTT):
    """Order mixin"""
    def list_orders(self, page=1, per_page=20, state=None,
                    team_identifier=None):
        """returns all orders of a user."""
        url = self.config['list_orders']
        params = self.params
        params.update({'page': page, 'per_page': per_page, 'state': state,
                       'team_identifier': team_identifier})
        return self.request_json(url, params=params, method='GET')

    def create_order(self, name=None, reference=None, comment=None,
                     coupon_code=None, desired_delivery_date=None,
                     service_level=None, cost_center_identifier=None):
        """create a new order"""
        url = self.config['create_order']
        data = self.params
        data.update({'name': name, 'reference': reference,
                     'commment': comment, 'coupon_code': coupon_code,
                     'desired_delivery_date': desired_delivery_date,
                     'service_level': service_level,
                     'cost_center_identifier': cost_center_identifier})
        return self.request_json(url, data=data, method='POST')

    def update_order(self, identifier, reference=None, name=None,
                     cost_center_identifier=None):
        """update an order"""
        url = self.config['update_order'].format(identifier=identifier)
        params = self.params
        params.update({'identifier': identifier, 'reference': reference,
                       'name': name,
                       'cost_center_identifier': cost_center_identifier})
        return self.request_json(url, params=params, method='PATCH')

    def show_order(self, identifier):
        """show an order"""
        url = self.config['show_order'].format(identifier=identifier)
        params = self.params
        params.update({'identifier': identifier})
        return self.request_json(url, params=params, method='GET')

    def request_order(self, identifier):
        """request an order"""
        url = self.config['request_order'].format(identifier=identifier)
        params = self.params
        params.update({'identifier': identifier})
        return self.request_json(url, params=params, method='PATCH')

    def rate_order(self, identifier):
        """rate an order"""
        url = self.config['rate_order'].format(identifier=identifier)
        data = self.params
        data.update({'identifier': identifier})
        return self.request_json(url, data=data, method='POST')


class DocumentMixin(AuthenticatedTT):
    """Document mixin"""
    def upload_document(self, token, document, document_type):
        """Upload a document"""
        url = self.config.document_store_url('upload_document')
        data = {"token": token, "type": document_type}
        return self.request_json(url, data=data,
                                 files={'file': open(document, 'rb')},
                                 method='POST')

    def download_document(self, token, identifier):
        """Download a document"""
        # url = self.config.document_store_url('download_document').format(
        #       identifier=identifier)
        # data = {"token": token}
        # return self.request_json(

    def list_documents(self, identifier):
        """List documents of an order"""
        url = self.config['list_documents'].format(identifier=identifier)
        params = self.params
        return self.request_json(url, params=params, method='GET')

    def add_document(self, identifier, document_store_id, document_token,
                     locale_code, target_locale_codes, name=None):
        """Add a document to an order"""
        url = self.config['add_document'].format(identifier=identifier)
        data = self.params
        data.update({'identifier': identifier,
                     'document_store_id': document_store_id,
                     'document_token': document_token,
                     'locale_code': locale_code,
                     'target_locale_codes': target_locale_codes,
                     'name': name})
        return self.request_json(url, data=data, method='POST')


class QuotesMixin(AuthenticatedTT):
    """Quotes mixin"""
    def list_quotes(self, identifier):
        """List quotes of an order"""
        url = self.config['list_quotes'].format(identifier=identifier)
        params = self.params
        return self.request_json(url, params=params, method='GET')


class InvoicesMixin(AuthenticatedTT):
    """Invoices mixin"""
    def list_invoices(self, identifier):
        """List invoices of an order"""
        url = self.config['list_invoices'].format(identifier=identifier)
        params = self.params
        return self.request_json(url, params=params, method='GET')


class Toptranslation(OrderMixin, DocumentMixin, QuotesMixin, InvoicesMixin):
    """Provides access to Toptranslation's API"""

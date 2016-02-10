"""Internal helper functions"""

import sys
from requests import Request


def _prepare_request(session, url, params, data, auth, files,
                     method=None):
    """Return a requests Request object that can be "prepared"."""
    # Requests using OAuth for authorization must switch to using the oauth
    # domain.
    if getattr(session, '_use_oauth', False):
        bearer = 'bearer {0}'.format(session.access_token)
        headers = {'Authorization': bearer}
        config = session.config
        for prefix in (config.api_url, config.permalink_url):
            if url.startswith(prefix):
                if config.log_requests >= 1:
                    msg = 'substituting {0} for {1} in url\n'.format(
                        config.oauth_url, prefix)
                    sys.stderr.write(msg)
                url = config.oauth_url + url[len(prefix):]
                break
    else:
        headers = {}
    headers.update(session.http.headers)

    if method:
        pass
    elif data or files:
        method = 'POST'
    else:
        method = 'GET'

    # Log the request if logging is enabled
    if session.config.log_requests >= 1:
        sys.stderr.write('{0}: {1}\n'.format(method, url))
    if session.config.log_requests >= 2:
        if params:
            sys.stderr.write('params: {0}\n'.format(params))
        if data:
            sys.stderr.write('data: {0}\n'.format(data))
        if auth:
            sys.stderr.write('auth: {0}\n'.format(auth))
    # Prepare request
    request = Request(method=method, url=url, headers=headers, params=params,
                      auth=auth, cookies=session.http.cookies)
    if method == 'GET':
        return request
    # Most POST requests require adding `api_type` and `uh` to the data.
    if data is True:
        data = {}

    if isinstance(data, dict):
        if not auth:
            data.setdefault('api_type', 'json')
    else:
        request.headers.setdefault('Content-Type', 'application/json')

    request.data = data
    request.files = files
    return request

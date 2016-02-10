
class ToptranslationObject(object):
    """Base class that represents an Toptranslation API object"""

    @classmethod
    def from_api_response(cls, session, json_dict):
        """Return an instance of the appropriate class from the json_dict."""
        return cls(session, json_dict=json_dict)

    def __init__(self, session, json_dict=None):
        """Create a new object from the dict of attributes"""
        self.session = session

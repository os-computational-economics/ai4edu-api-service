"""This type stub file was generated by pyright."""

class PineconeException(Exception):
    """The base exception class for all exceptions in the Pinecone Python SDK"""

class PineconeApiTypeError(PineconeException, TypeError):
    def __init__(self, msg, path_to_item=..., valid_classes=..., key_type=...) -> None:
        """Raises an exception for TypeErrors

        Args:
            msg (str): the exception message

        Keyword Args:
            path_to_item (list): a list of keys an indices to get to the
                                 current_item
                                 None if unset
            valid_classes (tuple): the primitive classes that current item
                                   should be an instance of
                                   None if unset
            key_type (bool): False if our value is a value in a dict
                             True if it is a key in a dict
                             False if our item is an item in a list
                             None if unset

        """

class PineconeApiValueError(PineconeException, ValueError):
    def __init__(self, msg, path_to_item=...) -> None:
        """Args:
            msg (str): the exception message

        Keyword Args:
            path_to_item (list) the path to the exception in the
                received_data dict. None if unset

        """

class PineconeApiAttributeError(PineconeException, AttributeError):
    def __init__(self, msg, path_to_item=...) -> None:
        """Raised when an attribute reference or assignment fails.

        Args:
            msg (str): the exception message

        Keyword Args:
            path_to_item (None/list) the path to the exception in the
                received_data dict

        """

class PineconeApiKeyError(PineconeException, KeyError):
    def __init__(self, msg, path_to_item=...) -> None:
        """Args:
            msg (str): the exception message

        Keyword Args:
            path_to_item (None/list) the path to the exception in the
                received_data dict

        """

class PineconeApiException(PineconeException):
    def __init__(self, status=..., reason=..., http_resp=...) -> None: ...
    def __str__(self) -> str:
        """Custom error messages for exception"""

class NotFoundException(PineconeApiException):
    def __init__(self, status=..., reason=..., http_resp=...) -> None: ...

class UnauthorizedException(PineconeApiException):
    def __init__(self, status=..., reason=..., http_resp=...) -> None: ...

class ForbiddenException(PineconeApiException):
    def __init__(self, status=..., reason=..., http_resp=...) -> None: ...

class ServiceException(PineconeApiException):
    def __init__(self, status=..., reason=..., http_resp=...) -> None: ...

def render_path(path_to_item):  # -> str:
    """Returns a string representation of a path"""

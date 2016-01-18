from functools import wraps

from . import Endpoint


def endpoint(path, method):
    endpoint_ = Endpoint(path, method)

    def decorator(func):
        Endpoint.endpoints[(endpoint_.resource.path, method)] = endpoint_

        @wraps(func)
        def wrapper(event, context):
            return func(event, context)
        return wrapper

    return decorator

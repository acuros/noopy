from . import Endpoint


def endpoint(path, method):
    def decorator(func):
        endpoint_ = Endpoint(path, method)
        Endpoint.endpoints[endpoint_] = func
        return func

    return decorator

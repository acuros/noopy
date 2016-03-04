import boto3

from noopy import lambda_functions
from noopy.endpoint import Endpoint
from noopy.utils import to_pascal_case


def lambda_function(func):
    lambda_functions.append(func)
    return func


def endpoint(path, method):
    def decorator(func):
        func = lambda_function(func)

        methods = []
        try:
            iter(method)
            methods = method
        except TypeError:
            methods.append(method)

        for method_ in methods:
            endpoint_ = Endpoint(path, method_)
            Endpoint.endpoints[endpoint_] = func
        return func

    return decorator

import boto3

from noopy import lambda_functions
from noopy.cron.rule import BaseEventRule
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


def cron(rule):
    """
    :type rule: BaseEventRule
    """
    if not isinstance(rule, BaseEventRule):
        raise TypeError('Parameter "rule" must be an instance of BaseEventRule')

    def decorator(func):
        func = lambda_function(func)
        rule.functions.append(func)
        return func

    return decorator

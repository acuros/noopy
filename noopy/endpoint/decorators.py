import boto3

from noopy.utils import to_pascal_case
from noopy.endpoint import Endpoint


def endpoint(path, method):
    def decorator(func):
        from noopy import settings
        lambda_settings = settings.LAMBDA
        client = boto3.client('lambda')
        function_prefix = 'arn:aws:lambda:{}:{}:function:{}'.format(
            client._client_config.region_name,
            settings.ACCOUNT_ID,
            lambda_settings['Prefix']
        )
        pascal_name = to_pascal_case(func.func_name)
        func.arn = '{}{}'.format(function_prefix, pascal_name)
        func.lambda_name = '{}{}'.format(
            lambda_settings['Prefix'],
            pascal_name
        )

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

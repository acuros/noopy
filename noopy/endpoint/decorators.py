import boto3

from noopy.utils import to_pascal_case
from noopy.endpoint import Endpoint


def endpoint(path, method):
    def decorator(func):
        import settings
        lambda_settings = settings.LAMBDA
        client = boto3.client('lambda')
        function_prefix = 'arn:aws:lambda:{}:{}:{}'.format(
                client._client_config.region_name,
                settings.ACCOUNT_ID,
                lambda_settings['Prefix']
        )
        func.name_for_lambda = '{}{}'.format(function_prefix, to_pascal_case(func.func_name))
        endpoint_ = Endpoint(path, method)
        Endpoint.endpoints[endpoint_] = func
        return func

    return decorator

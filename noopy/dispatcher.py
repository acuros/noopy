from noopy import lambda_functions
from noopy.endpoint import Endpoint
from noopy.endpoint import methods


def dispatch(event, context):
    print event

    if event['type'] == 'APIGateway':
        path = event['path']
        method = getattr(methods, event['method'])
        endpoint = Endpoint.endpoints[Endpoint(path, method)]
        return endpoint(event.get('params', {}), context)

    if event['type'] == 'Lambda':
        funcs = [f for f in lambda_functions if f.func_name == event['function_name']]
        if len(funcs) != 1:
            raise ValueError('One and only one function "{}" needed.'.format(event['function_name']))
        funcs[0](event.get('params', {}), context)

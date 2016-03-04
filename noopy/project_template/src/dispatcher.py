from noopy.endpoint import Endpoint
from noopy.endpoint import methods
import settings

for module in settings.LAMBDA_MODULES:
    __import__(module)


def dispatch(event, context):
    if 'type' not in event:
        raise ValueError('event has no "type"')

    if event['type'] == 'APIGateway':
        path = event['path']
        method = getattr(methods, event['method'])
        endpoint = Endpoint.endpoints[Endpoint(path, method)]

        return endpoint(event.get('params', dict()), context)

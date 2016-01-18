from noopy.endpoint import methods
from noopy.endpoint.decorators import endpoint


@endpoint('/foo', methods.GET)
def sample_view(event, context):
    pass


def test_resources_added():
    from noopy.endpoint.resource import Resource

    resources = Resource.resources
    assert set(resources.keys()) == {'/', '/foo'}
    assert resources['/'].children == [resources['/foo']]
    assert resources['/foo'].parent == resources['/']


def test_endpoints_added():
    from noopy.endpoint import Endpoint

    endpoints = Endpoint.endpoints
    foo_endpoint = Endpoint('/foo', methods.GET)
    assert set(endpoints.keys()) == {foo_endpoint}
    assert endpoints[foo_endpoint] == sample_view
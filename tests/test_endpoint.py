import pytest

from noopy.endpoint import methods
from noopy.decorators import endpoint


def simple_view(event, context):
    return {}


@pytest.fixture
def single_ep_view():
    return endpoint('/foo', methods.GET)(simple_view)


@pytest.fixture
def double_ep_view():
    view = endpoint('/foo', methods.PUT)(simple_view)
    return endpoint('/foo', methods.POST)(view)


def test_resources_added(single_ep_view):
    from noopy.endpoint.resource import Resource

    resources = Resource.resources
    assert set(resources.keys()) == {'/', '/foo'}
    assert resources['/'].children == [resources['/foo']]
    assert resources['/foo'].parent == resources['/']


def test_endpoints_added(single_ep_view):
    from noopy.endpoint import Endpoint

    endpoints = Endpoint.endpoints
    foo_endpoint = Endpoint('/foo', methods.GET)
    assert set(endpoints.keys()) == {foo_endpoint}
    assert endpoints[foo_endpoint] == single_ep_view


def test_multiple_endpoints(double_ep_view):
    from noopy.endpoint import Endpoint
    from noopy.endpoint.resource import Resource

    assert set(Resource.resources.keys()) == {'/', '/foo'}
    assert set(Endpoint.endpoints.keys()) == {Endpoint('/foo', methods.PUT), Endpoint('/foo', methods.POST)}

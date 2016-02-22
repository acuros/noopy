def pytest_runtest_teardown():
    from noopy.endpoint.resource import Resource
    from noopy.endpoint import Endpoint

    Resource.resources = {'/': Resource('/')}
    Endpoint.endpoints = {}

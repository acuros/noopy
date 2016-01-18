from .resource import Resource


class Endpoint(object):
    endpoints = {}

    def __init__(self, path, method):
        resource = Resource.resources.get(path)
        if not resource:
            resource = Resource(path)
        self.resource = resource

from collections import namedtuple

from .resource import Resource


class Endpoint(namedtuple('Endpoint', ['path', 'method'])):
    endpoints = {}

    def __init__(self, path, method):
        self.resource = Resource(self.path)

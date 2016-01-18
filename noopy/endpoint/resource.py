import re


class Resource(object):
    resources = {}

    def __new__(cls, path):
        if path in cls.resources:
            return cls.resources[path]
        return super(Resource, cls).__new__(cls, path)

    def __init__(self, path):
        self.path = self._validate_path(path)
        self.children = []
        if self.path != '/':
            self.parent = self._resolve_parent(self.path)
            Resource.resources[self.parent.path].register_child(self)
            Resource.resources[self.path] = self

    def register_child(self, child):
        self.children.append(child)

    @staticmethod
    def _resolve_parent(path):
        parents = path.split('/')[1:-1]
        if not parents:
            return Resource.resources['/']

        for i, parent in enumerate(parents):
            parent_path = '/{}'.format('/'.join(parents[:i + 1]))
            parent_resource = Resource.resources.get(parent_path)
            if not parent_resource:
                Resource.resources[parent_path] = Resource(parent_path)
                parent_resource.register_child(Resource.resources[parent_path])
        return '/{}'.format('/'.join(parents))

    @staticmethod
    def _validate_path(path):
        if not isinstance(path, basestring):
            raise TypeError('The type of resource must be instance of basestring')

        resource_pattern = r'^/[~0-9a-zA-Z\+%@\./_-{}]*$'
        if not re.match(resource_pattern, path):
            raise ValueError('Resource must satisfy regular express pattern: {}'.format(resource_pattern))

        new_path = re.sub(r'/{2,}', '/', path)
        if path != new_path:
            print 'Warning: there is "//" in "{}"'.format(new_path)
        return new_path


Resource.resources['/'] = Resource('/')

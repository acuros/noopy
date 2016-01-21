class MethodType(type):
    def __str__(self):
        return self.__name__


class BaseMethod(object):
    __metaclass__ = MethodType


class GET(BaseMethod):
    pass


class POST(BaseMethod):
    pass


class PUT(BaseMethod):
    pass


class DELETE(BaseMethod):
    pass


class PATCH(BaseMethod):
    pass


class HEAD(BaseMethod):
    pass

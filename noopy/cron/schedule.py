class BaseEventRule(object):
    rules = dict()

    def __init__(self, name):
        self.rules[name] = self

    @property
    def expression(self):
        raise NotImplementedError


class RateEventRule(BaseEventRule):
    UNIT_MINIUTES = 'minutes'
    UNIT_HOURS = 'hours'
    UNIT_DAYS = 'days'

    def __init__(self, name, value, unit='minutes'):
        if not isinstance(value, int):
            raise TypeError('Parameter "value" must be type of "int", not "%s"' % str(type(value)))

        units = [getattr(self, key) for key in dir(self) if key.startswith('UNIT_')]
        if unit not in units:
            raise ValueError('Parameter "unit" must be one of %s' % ','.join(units))

        super(RateEventRule, self).__init__(name)

        self.name = name
        self.value = value
        self.unit = unit

    @property
    def expression(self):
        return 'rate(%d %s)' % (self.value, self.unit)


class TimeEventRule(BaseEventRule):
    def __init__(self, name, pattern):
        if not isinstance(pattern, basestring):
            raise TypeError('Parameter "expression" must be type of "string", not "%s"' % str(type(pattern)))

        super(TimeEventRule, self).__init__(name)

        self.name = name
        self.pattern = pattern

    @property
    def expression(self):
        return 'cron(%s)' % self.pattern

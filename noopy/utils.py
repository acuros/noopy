def to_pascal_case(string):
    return ''.join([w.title() for w in string.split('_')])



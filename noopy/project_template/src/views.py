from noopy.endpoint.decorators import endpoint
from noopy.endpoint.methods import GET


@endpoint('/', GET)
def home(event, context):
    return ''

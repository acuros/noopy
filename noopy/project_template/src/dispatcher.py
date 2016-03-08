import settings

for module in settings.LAMBDA_MODULES:
    __import__(module)

from noopy.dispatcher import dispatch

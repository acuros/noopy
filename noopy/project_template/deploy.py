#!/usr/bin/python
import sys

from noopy import deploy
import settings

if __name__ == '__main__':
    if len(sys.argv) == 2:
        stage = sys.argv[1]
    else:
        stage = 'prod'
    deploy.deploy(settings, stage)

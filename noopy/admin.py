#!/usr/bin/python
import os
import pkgutil
import sys
from importlib import import_module

import noopy


class BaseCommand(object):
    @property
    def commands(self):
        command_path = os.path.join(noopy.__path__[0], 'commands')
        return [name for _, name, is_pkg in pkgutil.iter_modules([command_path])
                if not is_pkg and not name.startswith('_')]

    def show_usage(self, message=''):
        sys.stderr.write('Usage: noopy-admin <command>\n\n')
        sys.stderr.write('Available commands:\n')
        for command in self.commands:
            sys.stderr.write('\t{}\n'.format(command))
        if message:
            sys.stderr.write('\nError: {}\n'.format(message))
        sys.exit(1)


class NoopyAdmin(BaseCommand):
    def handle(self, *options):
        if not options:
            self.show_usage('No command specified')
        command = options[0]
        if command not in self.commands:
            self.show_usage('No such command "{}"'.format(command))
        module = import_module('noopy.commands.{}'.format(command))
        command = getattr(module, 'Command')()
        command.handle(*options[1:])


def main():
    NoopyAdmin().handle(*sys.argv[1:])


if __name__ == '__main__':
    main()

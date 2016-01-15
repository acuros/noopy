#!/usr/bin/python
import os
import shutil
import sys


class NoopyAdmin(object):
    @property
    def commands(self):
        return [attr[len('_do_'):] for attr in dir(self) if attr.startswith('_do_')]

    def run(self, *options):
        if not options:
            self.show_usage('No command specified')
        command = options[0]
        if command not in self.commands:
            self.show_usage('No such command "{}"'.format(command))
        getattr(self, '_do_{}'.format(command))(*options[1:])

    def show_usage(self, message=''):
        sys.stderr.write('Usage: noopy-admin <command>\n\n')
        sys.stderr.write('Available commands:\n')
        for command in self.commands:
            sys.stderr.write('\t{}\n'.format(command))
        if message:
            sys.stderr.write('\nError: {}\n'.format(message))
        sys.exit(1)

    def _do_startproject(self, *options):
        if not options:
            self.show_usage('You must provide a project name')
        project_name = options[0]
        module_directory = os.path.split(os.path.realpath(__file__))[0]
        template_dir = os.path.join(module_directory, 'project_template')
        shutil.copytree(template_dir, project_name)
        os.mkdir(os.path.join(project_name, 'src'))


if __name__ == '__main__':
    NoopyAdmin().run(*sys.argv[1:])

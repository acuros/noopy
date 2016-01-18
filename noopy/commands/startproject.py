import glob
import os
from string import Template

import noopy
from noopy.admin import BaseCommand


def to_pascal_case(string):
    return ''.join([w.title() for w in string.split('_')])


class Command(BaseCommand):
    def handle(self, *options):
        if not options:
            self.show_usage('You must provide a project name')
        project_name = options[0]
        template_dir = os.path.join(noopy.__path__[0], 'project_template')

        os.mkdir(project_name)
        os.mkdir(os.path.join(project_name, 'src'))

        context = dict(
            project_name=project_name,
            lambda_prefix=to_pascal_case(project_name),
        )
        for file_path in glob.glob('{}/*.py'.format(template_dir)):
            with open(file_path, 'r') as f:
                content = f.read()
            filename = os.path.split(file_path)[1]
            with open(os.path.join(project_name, filename), 'w') as f:
                f.write(Template(content).substitute(**context))

        print 'Project "{}" created'.format(project_name)

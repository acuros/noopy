import glob
import os
import shutil

import noopy
from noopy.admin import BaseCommand


class Command(BaseCommand):
    def handle(self, *options):
        if not options:
            self.show_usage('You must provide a project name')
        project_name = options[0]
        template_dir = os.path.join(noopy.__path__[0], 'project_template')

        os.mkdir(project_name)
        os.mkdir(os.path.join(project_name, 'src'))
        for file_name in glob.glob('{}/*.py'.format(template_dir)):
            shutil.copy(file_name, project_name)

        print 'Project "{}" created'.format(project_name)

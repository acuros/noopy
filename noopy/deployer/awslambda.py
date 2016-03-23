import importlib
import os
import sys
import zipfile
from StringIO import StringIO

import boto3
import pip

from noopy import settings
from noopy.utils import to_pascal_case


class LambdaDeployer(object):
    client = boto3.client('lambda')

    def __init__(self, function_arn, stage):
        self.function_arn = function_arn
        self.stage = stage
        self.function_name = function_arn.split(':')[-1]

    def deploy(self, dir_):
        zip_bytes = self._make_zip(dir_)

        exist_function_names = {
            f['FunctionName']
            for f in self.client.list_functions()['Functions']
        }

        if to_pascal_case(self.function_name) in exist_function_names:  # TODO: Control when user has lots of lambda functions
            self._update_function(zip_bytes)
        else:
            self._create_lambda_function(zip_bytes)

    def _make_zip(self, target_dir):
        f = StringIO()
        zip_file = zipfile.ZipFile(f, 'w')

        for root, dirs, files in os.walk(target_dir):
            for file_ in files:
                full_path = os.path.join(root, file_)
                zip_file.write(full_path)

        if not zip_file.filelist:
            sys.stderr.write('There is no file in src directory')
            sys.exit(1)

        packages = reduce(lambda x, y: x | self._requirements(y), set(settings.PACKAGE_REQUIREMENTS), set())
        packages -= {'boto3', 'botocore'}
        for package_name in packages:
            module = importlib.import_module(package_name)
            has_module_path = hasattr(module, '__path__') and module.__path__
            module_path = module.__path__[0] if has_module_path else module.__file__[:-1]
            module_parent_dir = os.path.dirname(module_path)
            if not has_module_path:
                zip_file.write(module_path, module_path[len(module_parent_dir):])
                continue
            for root, _, file_names in os.walk(module.__path__[0]):
                for file_name in file_names:
                    full_path = os.path.join(root, file_name)
                    local_path = full_path[len(module_parent_dir):]
                    zip_file.write(full_path, local_path)
        zip_file.write('settings.py')
        zip_file.write('dispatcher.py')

        stage_settings = '{}_settings.py'.format(self.stage)
        if os.path.isfile(stage_settings):
            zip_file.write(stage_settings, 'local_noopy_settings.py')
        zip_file.close()

        f.seek(0)
        bytes_ = f.read()
        f.close()

        return bytes_

    def _requirements(self, package_name):
        def _get_package(_package_name):
            candidates = [p for p in pip.get_installed_distributions() if p.project_name == _package_name]
            if not candidates:
                raise ValueError('No package "{}"'.format(package_name))
            return candidates[0]

        package = _get_package(package_name)
        result = set(name for name in package._get_metadata("top_level.txt") if '/' not in name)
        for requirement in package.requires():
            result |= self._requirements(requirement.project_name)
        return result

    def _update_function(self, zip_bytes):
        lambda_settings = settings.LAMBDA

        self.client.update_function_code(
            FunctionName=self.function_arn,
            ZipFile=zip_bytes
        )
        self.client.update_function_configuration(
            FunctionName=self.function_arn,
            Role=lambda_settings['Role'],
            Handler='dispatcher.dispatch'
        )

    def _create_lambda_function(self, zip_bytes):
        lambda_settings = settings.LAMBDA

        self.client.create_function(
            FunctionName=self.function_arn,
            Runtime='python2.7',
            Role=lambda_settings['Role'],
            Handler='dispatcher.dispatch',
            Code={
                'ZipFile': zip_bytes
            }
        )
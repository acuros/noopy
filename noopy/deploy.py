import glob
import importlib
import os
import pip
import shutil
import sys
import zipfile
from StringIO import StringIO

import boto3
from botocore.exceptions import ClientError

import noopy
from noopy import settings
from noopy.endpoint import Endpoint
from noopy.endpoint.resource import Resource


def deploy(settings_module):
    sys.path.append(os.path.join(os.getcwd(), 'src'))
    settings.load_project_settings(settings_module)
    LambdaDeployer().deploy('src')
    print ApiGatewayDeployer().deploy()


class LambdaDeployer(object):
    def __init__(self):
        self.client = boto3.client('lambda')
        self.exist_function_names = set()

    def deploy(self, dir_):
        self._discover_endpoints(dir_)
        zip_bytes = self._make_zip(dir_)

        self.exist_function_names = {
            f['FunctionName']
            for f in self.client.list_functions()['Functions']
            if f['FunctionName'].startswith(settings.LAMBDA['Prefix'])
        }

        names = set()
        for func in noopy.lambda_functions:
            if func.lambda_name in names:
                continue
            names.add(func.lambda_name)
            if func.lambda_name in self.exist_function_names:  # TODO: Control when user has lots of lambda functions
                self._update_function(zip_bytes, func)
            else:
                self._create_lambda_function(zip_bytes, func)

    def _discover_endpoints(self, module):
        for endpoint in settings.LAMBDA_MODULES:
            importlib.import_module('{}.{}'.format(module, endpoint))

    def _make_zip(self, target_dir):
        f = StringIO()
        zip_file = zipfile.ZipFile(f, 'w')

        for root, dirs, files in os.walk(target_dir):
            for file_ in files:
                full_path = os.path.join(root, file_)
                zip_file.write(full_path, full_path[len(target_dir):])

        if not zip_file.filelist:
            sys.stderr.write('There is no file in src directory')
            sys.exit(1)

        packages = reduce(lambda x, y: x | self._requirements(y), set(settings.PACKAGE_REQUIREMENTS), set())
        for package_name in packages:
            module = importlib.import_module(package_name)
            module_path = module.__path__[0] if module.__path__ else module.__file__[:-1]
            module_parent_dir = os.path.dirname(module_path)
            if not module.__path__:
                zip_file.write(module_path, module_path[len(module_parent_dir):])
                continue
            for root, _, file_names in os.walk(module.__path__[0]):
                for file_name in file_names:
                    full_path = os.path.join(root, file_name)
                    local_path = full_path[len(module_parent_dir):]
                    zip_file.write(full_path, local_path)
        zip_file.write('settings.py')
        zip_file.close()

        f.seek(0)
        bytes_ = f.read()
        f.close()

        return bytes_

    def _requirements(self, package_name):
        def _get_package(_package_name):
            return [p for p in pip.get_installed_distributions() if p.project_name == _package_name][0]
        package = _get_package(package_name)
        result = set(name for name in package._get_metadata("top_level.txt") if '/' not in name)
        for requirement in package.requires():
            result |= self._requirements(requirement.project_name)
        return result

    def _update_function(self, zip_bytes, func):
        lambda_settings = settings.LAMBDA
        func_module = os.path.split(func.func_code.co_filename)[1].split('.')[0]

        self.client.update_function_code(
            FunctionName=func.arn,
            ZipFile=zip_bytes
        )
        self.client.update_function_configuration(
            FunctionName=func.arn,
            Role=lambda_settings['Role'],
            Handler='{}.{}'.format(func_module, func.func_name),
        )

    def _create_lambda_function(self, zip_bytes, func):
        lambda_settings = settings.LAMBDA
        func_module = os.path.split(func.func_code.co_filename)[1].split('.')[0]

        self.client.create_function(
            FunctionName=func.arn,
            Runtime='python2.7',
            Role=lambda_settings['Role'],
            Handler='{}.{}'.format(func_module, func.func_name),
            Code={
                'ZipFile': zip_bytes
            }
        )


class ApiGatewayDeployer(object):
    def __init__(self):
        self.client = boto3.client('apigateway')
        apis = self.client.get_rest_apis()['items']
        filtered_apis = [api for api in apis if api['name'] == settings.PROJECT_NAME]
        if filtered_apis:
            self.api_id = filtered_apis[0]['id']
        else:
            self.api_id = self.client.create_rest_api(name=settings.PROJECT_NAME)['id']
        self.aws_resources = self.client.get_resources(restApiId=self.api_id, limit=500)['items']

    def deploy(self):
        if not Endpoint.endpoints:
            return
        self.deploy_resources()
        self.deploy_methods()
        self.deploy_stage()
        return 'https://{}.execute-api.{}.amazonaws.com/prod'.format(
            self.api_id,
            self.client._client_config.region_name,
        )

    def deploy_resources(self):
        aws_resources = self.client.get_resources(restApiId=self.api_id, limit=500)['items']
        aws_resource_by_path = dict((r['path'], r) for r in aws_resources)
        for path, noopy_resource in Resource.resources.iteritems():
            aws_resource = aws_resource_by_path.get(path)
            if aws_resource:
                noopy_resource.id = aws_resource['id']

        self.create_omitted_resources(set(aws_resource_by_path.keys()), Resource.resources['/'])

    def deploy_methods(self):
        aws_resources = self.client.get_resources(restApiId=self.api_id, limit=500)['items']
        aws_resource_by_path = dict((r['path'], r) for r in aws_resources)
        for endpoint, func in Endpoint.endpoints.iteritems():
            method = str(endpoint.method)
            aws_resource = aws_resource_by_path.get(endpoint.path)
            if method not in aws_resource.get('resourceMethods', {}):
                self.client.put_method(
                    restApiId=self.api_id,
                    resourceId=aws_resource['id'],
                    httpMethod=method,
                    authorizationType=''
                )
                lambda_client = boto3.client('lambda')
                source_arn = 'arn:aws:execute-api:{}:{}:{}/*/*/*'.format(
                    self.client._client_config.region_name,
                    settings.ACCOUNT_ID,
                    self.api_id
                )

                try:
                    lambda_client.add_permission(
                        FunctionName=func.arn,
                        StatementId='1',
                        Action='lambda:InvokeFunction',
                        Principal='apigateway.amazonaws.com',
                        SourceArn=source_arn
                    )
                except ClientError:
                    pass
                uri = 'arn:aws:apigateway:{}:lambda:path/2015-03-31/functions/{}/invocations'.format(
                    self.client._client_config.region_name,
                    func.arn
                )
                self.client.put_integration(
                    restApiId=self.api_id,
                    resourceId=aws_resource['id'],
                    httpMethod=method,
                    integrationHttpMethod='POST',
                    type='AWS',
                    uri=uri,
                )
                self.client.put_method_response(
                    restApiId=self.api_id,
                    resourceId=aws_resource['id'],
                    httpMethod=method,
                    statusCode='200',
                    responseModels={
                        'application/json': 'Empty'
                    }
                )
                self.client.put_integration_response(
                    restApiId=self.api_id,
                    resourceId=aws_resource['id'],
                    httpMethod=method,
                    statusCode='200',
                    selectionPattern=''
                )

    def deploy_stage(self):
        self.client.create_deployment(restApiId=self.api_id, stageName='prod')

    def create_omitted_resources(self, exist_path, parent):
        for child in parent.children:
            if child.path not in exist_path:
                created = self.client.create_resource(
                    restApiId=self.api_id,
                    parentId=parent.id,
                    pathPart=child.path.split('/')[-1]
                )
                exist_path.add(child.path)
                self.aws_resources.append(created)
                child.id = created['id']
            if child.children:
                self.create_omitted_resources(exist_path, child)

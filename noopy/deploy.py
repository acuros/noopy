import importlib
import os
import sys
import uuid
import zipfile
from StringIO import StringIO

import boto3
import pip
from botocore.exceptions import ClientError
from noopy.utils import to_pascal_case

from noopy import settings
from noopy.endpoint import Endpoint
from noopy.endpoint.resource import Resource


def deploy(settings_module, stage='prod'):
    sys.path.append(os.path.join(os.getcwd(), 'src'))
    settings.load_project_settings(settings_module)

    client = boto3.client('lambda')
    func_name = to_pascal_case('{}{}'.format(settings.LAMBDA['Prefix'], stage))
    function_arn = 'arn:aws:lambda:{}:{}:function:{}'.format(
        client._client_config.region_name,
        settings.ACCOUNT_ID,
        func_name
    )

    LambdaDeployer(function_arn, stage).deploy('src')
    print ApiGatewayDeployer(function_arn, stage).deploy('src')


class LambdaDeployer(object):
    def __init__(self, function_arn, stage):
        self.client = boto3.client('lambda')
        self.stage = stage
        self.function_arn = function_arn
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
            return [p for p in pip.get_installed_distributions() if p.project_name == _package_name][0]

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


class ApiGatewayDeployer(object):
    def __init__(self, function_arn, stage):
        self.function_arn = function_arn
        self.stage = stage

        self.client = boto3.client('apigateway')
        apis = self.client.get_rest_apis()['items']
        filtered_apis = [api for api in apis if api['name'] == settings.PROJECT_NAME]
        if filtered_apis:
            self.api_id = filtered_apis[0]['id']
        else:
            self.api_id = self.client.create_rest_api(name=settings.PROJECT_NAME)['id']
        self.aws_resources = self.client.get_resources(restApiId=self.api_id, limit=500)['items']

    def deploy(self, dir_):
        self._discover_endpoints(dir_)
        if not Endpoint.endpoints:
            return
        self.add_permision()

        self.deploy_resources()
        self.deploy_methods()
        self.deploy_stage()
        return 'https://{}.execute-api.{}.amazonaws.com/{}'.format(
            self.api_id,
            self.client._client_config.region_name,
            self.stage
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
        resources = self.client.get_resources(restApiId=self.api_id, limit=500)['items']
        resources_by_path = dict((r['path'], r) for r in resources)

        for endpoint, func in Endpoint.endpoints.iteritems():
            method = str(endpoint.method)
            aws_resource = resources_by_path.get(endpoint.path)
            if method not in aws_resource.get('resourceMethods', {}):
                self._deploy_method(aws_resource, method)

    def _deploy_method(self, resource, method):
        self.client.put_method(
            restApiId=self.api_id,
            resourceId=resource['id'],
            httpMethod=method,
            authorizationType=''
        )
        uri = 'arn:aws:apigateway:{}:lambda:path/2015-03-31/functions/{}/invocations'.format(
            self.client._client_config.region_name,
            self.function_arn
        )
        template = '{"path": "$context.resourcePath", "method": "$context.httpMethod",' \
                   '"params": $input.json(\'$\'), "type": "APIGateway"}'
        self.client.put_integration(
            restApiId=self.api_id,
            resourceId=resource['id'],
            httpMethod=method,
            integrationHttpMethod='POST',
            requestTemplates={
                'application/json': template
            },
            type='AWS',
            uri=uri,
        )
        self.client.put_method_response(
            restApiId=self.api_id,
            resourceId=resource['id'],
            httpMethod=method,
            statusCode='200',
            responseModels={
                'application/json': 'Empty'
            }
        )
        self.client.put_integration_response(
            restApiId=self.api_id,
            resourceId=resource['id'],
            httpMethod=method,
            statusCode='200',
            selectionPattern=''
        )

    def add_permision(self):
        lambda_client = boto3.client('lambda')
        source_arn = 'arn:aws:execute-api:{}:{}:{}/*/*/*'.format(
            self.client._client_config.region_name,
            settings.ACCOUNT_ID,
            self.api_id
        )
        try:
            lambda_client.add_permission(
                FunctionName=self.function_arn,
                StatementId=str(uuid.uuid1()),
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=source_arn
            )
        except ClientError:
            pass

    def deploy_stage(self):
        self.client.create_deployment(restApiId=self.api_id, stageName=self.stage)

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

    def _discover_endpoints(self, module):
        for lambda_module in settings.LAMBDA_MODULES:
            importlib.import_module(lambda_module)

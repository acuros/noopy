#!/usr/bin/python
import glob
import importlib
import os
import sys
import zipfile
from StringIO import StringIO

import boto3
import noopy
from noopy.endpoint import Endpoint
from noopy.endpoint.resource import Resource

import settings


def main():
    LambdaDeployer().deploy('src')
    print ApiGatewayDeployer().deploy()


class LambdaDeployer(object):
    def __init__(self):
        self.client = boto3.client('lambda')

    def deploy(self, dir_):
        self._discover_endpoints(dir_)
        zip_bytes = self._make_zip(dir_)

        exist_functions = [
            f['FunctionName']
            for f in self.client.list_functions()['Functions']
            if f['FunctionName'].startswith(settings.LAMBDA['Prefix'])
        ]
        for func in Endpoint.endpoints.values():
            if func.lambda_name in exist_functions:
                self._update_function(zip_bytes, func)
            else:
                self._create_lambda_function(zip_bytes, func)

    def _discover_endpoints(self, module):
        for endpoint in settings.ENDPOINTS:
            importlib.import_module('{}.{}'.format(module, endpoint))

    def _make_zip(self, target_dir):
        f = StringIO()
        zip_file = zipfile.ZipFile(f, 'w')

        file_names = glob.glob('{}/*.py'.format(target_dir))
        if not file_names:
            sys.stderr.write('There is no python file in src directory')
            sys.exit(1)

        for file_name in file_names:
            zip_file.write(file_name, os.path.split(file_name)[1])

        noopy_parent = os.path.split(noopy.__path__[0])[0]
        for root, _, file_names in os.walk(noopy.__path__[0]):
            for file_name in file_names:
                full_path = os.path.join(root, file_name)
                local_path = full_path[len(noopy_parent):]
                zip_file.write(full_path, local_path)

        zip_file.write('settings.py')

        zip_file.close()
        f.seek(0)
        bytes_ = f.read()
        f.close()

        return bytes_

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

        self.create_omitted_resources(aws_resource_by_path.keys(), Resource.resources['/'])

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
                source_arn = 'arn:aws:execute-api:{}:{}:{}/*/GET/'.format(
                    self.client._client_config.region_name,
                    settings.ACCOUNT_ID,
                    self.api_id
                )

                lambda_client.add_permission(
                    FunctionName=func.arn,
                    StatementId='1',
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=source_arn
                )
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
                self.aws_resources.append(created)
                child.id = created['id']
            if child.children:
                self.create_omitted_resources(exist_path, child)


if __name__ == '__main__':
    main()

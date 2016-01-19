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
from noopy.utils import to_pascal_case

import settings


def main():
    target_dir = 'src'
    zip_bytes = make_zip(target_dir)
    for endpoint in settings.ENDPOINTS:
        importlib.import_module('src.{}'.format(endpoint))

    for func in Endpoint.endpoints.values():
        create_lambda_function(zip_bytes, func)



def make_zip(target_dir):
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

    zip_file.close()
    f.seek(0)
    bytes_ = f.read()
    f.close()

    return bytes_


def create_lambda_function(zip_bytes, func):
    lambda_settings = settings.LAMBDA
    client = boto3.client('lambda')
    function_prefix = 'arn:aws:lambda:{}:{}:{}'.format(
            client._client_config.region_name,
            settings.ACCOUNT_ID,
            lambda_settings['Prefix']
    )
    func_module = os.path.split(func.func_code.co_filename)[1].split('.')[0]

    print client.create_function(
            FunctionName='{}{}'.format(function_prefix, to_pascal_case(func.func_name)),
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

    def prepare_resources(self):
        aws_resources = self.client.get_resources(restApiId=self.api_id, limit=500)['items']
        aws_resource_by_path = dict((r['path'], r) for r in aws_resources)
        for path, noopy_resource in Resource.resources.iteritems():
            aws_resource = aws_resource_by_path.get(path)
            if aws_resource:
                noopy_resource.id = aws_resource['id']

        self.create_omitted_resources(aws_resource_by_path.keys(), Resource.resources['/'])

    def create_omitted_resources(self, exist_path, parent):
        for child in parent.children:
            if child.path not in exist_path:
                created = self.client.create_resource(
                        restApiId=self.api_id,
                        parentId=parent.id,
                        pathPart=child.path.split('/')[-1]
                )
                child.id = created['id']
            if child.children:
                self.create_omitted_resources(exist_path, child)


if __name__ == '__main__':
    main()

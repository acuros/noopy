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


if __name__ == '__main__':
    main()

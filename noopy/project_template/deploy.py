#!/usr/bin/python
import glob
import os
import sys
import zipfile
from StringIO import StringIO

import boto3
import noopy
from noopy.utils import to_pascal_case

import settings


def main():
    target_dir = 'src'
    names, zip_bytes = make_zip(target_dir)
    for name in names:
        create_function(zip_bytes, name.rstrip('.py'))


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

    srcs = [name for name in zip_file.namelist() if '/' not in name]
    return srcs, bytes_


def create_function(zip_bytes, file_name):
    lambda_settings = settings.LAMBDA
    client = boto3.client('lambda')
    function_prefix = 'arn:aws:lambda:{}:{}:{}'.format(
            client._client_config.region_name,
            settings.ACCOUNT_ID,
            lambda_settings['Prefix']
    )

    print client.create_function(
            FunctionName='{}{}'.format(function_prefix, to_pascal_case(file_name)),
            Runtime='python2.7',
            Role=lambda_settings['Role'],
            Handler='{}.lambda_handler'.format(file_name),
            Code={
                'ZipFile': zip_bytes
            }
    )


if __name__ == '__main__':
    main()

import importlib
import uuid

import boto3
from botocore.exceptions import ClientError

from noopy import settings
from noopy.endpoint import Endpoint, Resource


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

    @property
    def function_uri(self):
        return 'arn:aws:apigateway:{}:lambda:path/2015-03-31/functions/{}/invocations'.format(
            self.client._client_config.region_name,
            self.function_arn
        )

    def deploy(self, dir_):
        self._discover_endpoints()
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
            resource = resources_by_path.get(endpoint.path)
            if method in resource.get('resourceMethods', {}):
                self._update_integration(resource, method)
            else:
                self._put_method(resource, method)

    def _update_integration(self, resource, method):
        self.client.update_integration(
            restApiId=self.api_id,
            resourceId=resource['id'],
            httpMethod=method,
            patchOperations=[
                {
                    'op': 'replace',
                    'path': '/uri',
                    'value': self.function_uri
                }
            ]
        )

    def _put_method(self, resource, method):
        self.client.put_method(
            restApiId=self.api_id,
            resourceId=resource['id'],
            httpMethod=method,
            authorizationType=''
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
            uri=self.function_uri,
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

    @staticmethod
    def _discover_endpoints():
        for lambda_module in settings.LAMBDA_MODULES:
            importlib.import_module(lambda_module)
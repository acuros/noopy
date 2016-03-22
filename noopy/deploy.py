import os
import sys

import boto3

from noopy import settings
from noopy.cron.rule import BaseEventRule
from noopy.deployer.apigateway import ApiGatewayDeployer
from noopy.deployer.awslambda import LambdaDeployer
from noopy.utils import to_pascal_case


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
    EventRuleDeployer().deploy()


class EventRuleDeployer(object):
    client = boto3.client('events')

    def deploy(self):
        existing_rules = self.client.list_rules()['Rules']  # TODO: Fetch all using NextToken
        existing_names = [r['Name'] for r in existing_rules]

        for rule in BaseEventRule.rules:
            if rule.name in existing_names:
                pass
            else:
                self._put_rule(rule)

    def _put_rule(self, rule):
        self.client.put_rule(Name=rule.name, ScheduleExpression=rule.expression)


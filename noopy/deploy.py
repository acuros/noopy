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
    func_name = '{}{}'.format(settings.LAMBDA['Prefix'], to_pascal_case(stage))
    function_arn = 'arn:aws:lambda:{}:{}:function:{}'.format(
        client._client_config.region_name,
        settings.ACCOUNT_ID,
        func_name
    )

    LambdaDeployer(function_arn, stage).deploy('src')
    print 'Lambda deployed'
    api_gateway_url = ApiGatewayDeployer(function_arn, stage).deploy('src')
    if api_gateway_url:
        print 'API Gateway URL: {}'.format(api_gateway_url)
    deployed_names = EventRuleDeployer().deploy()
    if deployed_names:
        print 'Deployed Event Rules:\n\t{}'.format('\n\t'.join(deployed_names))


class EventRuleDeployer(object):
    client = boto3.client('events')

    def deploy(self):
        existing_rules = self.client.list_rules()['Rules']  # TODO: Fetch all using NextToken
        existing_names = [r['Name'] for r in existing_rules]
        deployed_rule_names = []

        for rule_name, rule in BaseEventRule.rules.items():
            if rule_name in existing_names:
                pass
            else:
                self.client.put_rule(Name=rule.name, ScheduleExpression=rule.expression, State='ENABLED')
                deployed_rule_names.append(rule_name)

        return deployed_rule_names


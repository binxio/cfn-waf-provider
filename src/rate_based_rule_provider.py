from cfn_resource_provider import ResourceProvider
import boto3
import time
from botocore.exceptions import ClientError
import logging
import os

log = logging.getLogger()
log.setLevel(os.environ.get("LOG_LEVEL", "DEBUG"))

client = boto3.client('waf')


class RateBasedRuleProvider(ResourceProvider):
    def __init__(self):
        super(RateBasedRuleProvider, self).__init__()
        self.request_schema = {
            "type": "object",
            "required": ["Name", "MetricName", "RateKey", "RateLimit"],
            "properties": {
                "Name": {"type": "string"},
                "MetricName": {"type": "string"},
                "RateKey": {"type": "string"},
                "RateLimit": {"type": "integer"},
                "Action": {"type": "string"},
                "Negated": {"type": "boolean"},
                "Type": {"type": "string",
                         "description": "IPMatch | ByteMatch | SqlInjectionMatch | GeoMatch | SizeConstraint | "
                                        "XssMatch | RegexMatch"},
                "DataId": {"type": "string"}
            }
        }

    def create(self):
        kwargs = self.properties.copy()

        try:
            kwargs.pop('ServiceToken', None)
            kwargs.pop('Action', None)
            kwargs.pop('Negated', None)
            kwargs.pop('Type', None)
            kwargs.pop('DataId', None)

            kwargs.update({'ChangeToken': client.get_change_token()['ChangeToken']})
            response = client.create_rate_based_rule(**kwargs)

            self.physical_resource_id = response['Rule']['RuleId']

            status = self.wait_on_status(response['ChangeToken'], current_retry=0)   # wait for the rule to finish creating

            if status['Success']:
                if not self.missing_fields(kwargs):   # check if the rule needs to be updated with a predicate
                    print('Predicate detected in create request. Also updating the rule.')
                    self.update()

                    if status['Success']:
                        print('Create and update are done.')
                        self.success('Create and update are done.')
                else:
                    print('Create is done.')
                    self.success('Create is done.')
            else:
                self.fail(status['Reason'])
        except ClientError as error:
            self.physical_resource_id = 'failed-to-create'
            self.fail(f'{error}')

    def update(self):
        kwargs = self.properties.copy()
        kwargs.update({'RuleId': self.physical_resource_id})
        missing = self.missing_fields(kwargs)

        if not missing:
            try:
                updates = {
                    'Updates': {
                        'Action': kwargs['Action'],
                        'Predicate': {
                            'Negated': kwargs['Negated'],
                            'Type': kwargs['Type'],
                            'DataId': kwargs['DataId']
                        }
                    }
                }
                kwargs.update(updates)
                kwargs.pop('ServiceToken', None)

                kwargs.update({'ChangeToken': client.get_change_token()['ChangeToken']})

                response = client.update_rate_based_rule(**kwargs)
            except ClientError as error:
                self.fail(f'{error}')

            status = self.wait_on_status(response['ChangeToken'], current_retry=0)   # wait for the rule to finish updating

            if status['Success']:
                print('Update is done.')
                self.success('Update is done.')
            else:
                self.fail(status['Reason'])
        else:
            self.fail(f"Missing required fields: {missing}")

    def delete(self):
        kwargs = {'RuleId': self.physical_resource_id}

        try:
            kwargs.update({'ChangeToken': client.get_change_token()['ChangeToken']})
            response = client.delete_rate_based_rule(**kwargs)

            status = self.wait_on_status(response['ChangeToken'], current_retry=0)   # wait for the rule to finish deleting

            if status['Success']:
                print('Delete is done.')
                self.success('Delete is done.')
            else:
                self.fail(status['Reason'])
        except ClientError as error:
            if 'WAFNonexistentItemException' in error.response['Error']['Code']:
                self.success()
            else:
                self.fail(f'{error}')

    def wait_on_status(self, change_token, current_retry, interval=10, max_interval=30, max_retries=15):
        try:
            response = client.get_change_token_status(ChangeToken=change_token)

            if response['ChangeTokenStatus'] != 'INSYNC':
                if current_retry >= max_retries:
                    print(f"Max reties ({max_retries}) reached, something must have gone wrong. "
                          f"Current status: {response['ChangeTokenStatus']}.")
                    return {
                        "Success": False,
                        "Reason": f"Max retries ({max_retries}) reached, something must have gone wrong."
                    }
                else:
                    print(f"Not done, current status is: {response['ChangeTokenStatus']}. "
                          f"Waiting {interval} seconds before retrying.")
                    time.sleep(interval)
                    return self.wait_on_status(change_token,
                                               current_retry=current_retry + 1,
                                               interval=max(interval + interval, max_interval))
            else:
                return {"Success": True, "Reason": ""}
        except ClientError as error:
            self.physical_resource_id = 'failed-to-create'
            self.fail(f'{error}')

    def missing_fields(self, kwargs):
        required_fields = ['Action', 'Negated', 'Type', 'DataId']

        return set(required_fields) - set(kwargs)

    def convert_property_types(self):
        self.heuristic_convert_property_types(self.properties)


provider = RateBasedRuleProvider()


def handler(request, context):
    return provider.handle(request, context)

from cfn_resource_provider import ResourceProvider
import boto3
import time
from botocore.exceptions import ClientError

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
            kwargs.update({'ChangeToken': client.get_change_token()['ChangeToken']})
            kwargs.pop('ServiceToken', None)

            response = client.create_rate_based_rule(**kwargs)

            self.physical_resource_id = response['Rule']['RuleId']

            status = self.wait_on_status(response['ChangeToken'])   # wait for the rule to finish creating

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
        missing = self.missing_fields(kwargs)

        if not missing:
            try:
                kwargs.update({'ChangeToken': client.get_change_token()['ChangeToken']})

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

                response = client.update_rate_based_rule(**kwargs)
            except ClientError as error:
                self.fail(f'{error}')

            status = self.wait_on_status(response['ChangeToken'])   # wait for the rule to finish updating

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

            status = self.wait_on_status(response['ChangeToken'])   # wait for the rule to finish deleting

            if status['Success']:
                print('Delete is done.')
                self.success('Delete is done.')
            else:
                self.fail(status['Reason'])
        except ClientError as error:
            self.fail(f'{error}')

    def wait_on_status(self, change_token, interval=1, timeout=255):
        try:
            response = client.get_change_token_status(ChangeToken=change_token)

            if response['ChangeTokenStatus'] != 'INSYNC':
                if interval > timeout:
                    print(f"Timeout ({timeout}) reached, something must have gone wrong. "
                          f"Current status: {response['ChangeTokenStatus']}.")
                    return {"Success": False, "Reason": f"Timeout ({timeout}) reached, something must have gone wrong."}
                else:
                    print(f"Not done, current status is: {response['ChangeTokenStatus']}. "
                          f"Waiting {interval} seconds before retrying.")
                    time.sleep(interval)
                    return self.wait_on_status(change_token, interval=interval + interval)
            else:
                return {"Success": True, "Reason": ""}
        except ClientError as error:
            self.physical_resource_id = 'failed-to-create'
            self.fail(f'{error}')

    def missing_fields(self, kwargs):
        required_fields = ['Action', 'Negated', 'Type', 'DataId']

        return set(required_fields) - set(kwargs)


provider = RateBasedRuleProvider()


def handler(request, context):
    return provider.handle(request, context)

from mock import patch
from provider.rate_based_rule_provider import handler

import uuid

count = 0


def mock_boto_calls(self, operation_name, kwargs):
    if operation_name == 'CreateRateBasedRule':
        return {
            'Rule': {
                'RuleId': 'unique-id-123',
                'Name': 'unique-name-123',
                'MetricName': 'unique-name-123-metric',
                'MatchPredicates': [
                    {
                        'Negated': False,
                        'Type': 'IPMatch',
                        'DataId': 'unique-data-id-123'
                    },
                ],
                'RateKey': 'IP',
                'RateLimit': 2345
            },
            'ChangeToken': 'fake-change-token-1'
        }
    if operation_name == 'UpdateRateBasedRule':
        return {
            'ChangeToken': 'fake-change-token-2'
        }
    if operation_name == 'DeleteRateBasedRule':
        return {
            'ChangeToken': 'fake-change-token-3'
        }
    if operation_name == 'GetChangeToken':
        return {
            'ChangeToken': 'fake-change-token-1'
        }
    if operation_name == 'GetChangeTokenStatus':
        global count

        if count <= 2:
            count += 1

            return {
                'ChangeTokenStatus': 'PENDING'
            }
        else:
            return {
                'ChangeTokenStatus': 'INSYNC'
            }
    else:
        raise ValueError(f"Unknown operation name: '{operation_name}''")


@patch('botocore.client.BaseClient._make_api_call', mock_boto_calls)
def test_create_based_rate_rule():
    request = Request('Create', 'test-create-rate-based-rule', 2345)

    response = handler(request, ())

    print(f"create response: {response}")

    assert response['Status'] == 'SUCCESS'


@patch('botocore.client.BaseClient._make_api_call', mock_boto_calls)
def test_create_rate_based_rule_predicate():
    request = Request('Create', 'test-create-rate-based-rule-predicate', 2345, 'IP', 'INSERT',
                      None, 'IPMatch', 'unique-data-id-123')

    print(f"request: {request}")

    response = handler(request, ())

    print(f"create with predicate response: {response}")

    assert response['Status'] == 'SUCCESS'


@patch('botocore.client.BaseClient._make_api_call', mock_boto_calls)
def test_update_rate_based_rule_predicate():
    request = Request('Update', 'test-update-rate-based-rule-predicate', 2345, 'IP', 'INSERT',
                      False, 'IPMatch', 'unique-data-id-123')

    print(f"request: {request}")

    response = handler(request, ())

    print(f"update response: {response}")

    assert response['Status'] == 'SUCCESS'


@patch('botocore.client.BaseClient._make_api_call', mock_boto_calls)
def test_delete_rate_based_rule_predicate():
    request = Request('Delete', 'test-delete-rate-based-rule', 2345, 'IP')

    print(f"request: {request}")

    response = handler(request, ())

    print(f"delete response: {response}")

    assert response['Status'] == 'SUCCESS'


class Request(dict):

    def __init__(self, request_type, name, rate_limit, rate_key='IP',
                 action=None, negated=None, predicate_type=None, data_id=None, physical_resource_id=None):
        request_id = 'request-%s' % uuid.uuid4()
        self.update({
            'RequestType': request_type,
            'ResponseURL': 'https://httpbin.org/put',
            'StackId': 'arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid',
            'RequestId': request_id,
            'ResourceType': 'Custom::RateBasedRule',
            'LogicalResourceId': 'RateBasedRule',
            'ResourceProperties': {
                "Name": name,
                "MetricName": f"{name}-metric",
                "RateKey": rate_key,
                "RateLimit": rate_limit
            }})

        if action is not None:
            self['ResourceProperties']['Action'] = action
        if negated is not None:
            self['ResourceProperties']['Negated'] = negated
        if predicate_type is not None:
            self['ResourceProperties']['Type'] = predicate_type
        if data_id is not None:
            self['ResourceProperties']['DataId'] = data_id

        if physical_resource_id is not None:
            self['PhysicalResourceId'] = physical_resource_id

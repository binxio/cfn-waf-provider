from mock import patch
from src.rate_based_rule_provider import handler

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
                        'Type': 'ByteMatch',
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
    print(f"request: {request}")

    response = handler(request, ())
    print(f"create response: {response}")

    assert response['Status'] == 'SUCCESS'


@patch('botocore.client.BaseClient._make_api_call', mock_boto_calls)
def test_create_rate_based_rule_predicate():
    old_properties = {
        'Name': 'test-create-rate-based-rule-predicate',
        'MetricName': 'test-create-rate-based-rule-predicate-metric',
        'RateKey': 'IP',
        'RateLimit': 2345
    }
    updates = [
        {
            'Negated': False,
            'Type': 'IPMatch',
            'DataId': 'data-id-1'
        }
    ]

    request = Request('Create', 'test-create-rate-based-rule-predicate', 2345, 'IP', updates, old_properties)
    print(f"request: {request}")

    response = handler(request, ())
    print(f"create with predicate response: {response}")

    assert response['Status'] == 'SUCCESS'


@patch('botocore.client.BaseClient._make_api_call', mock_boto_calls)
def test_update_rule_with_new_predicate():
    # create a rule
    request = Request('Create', 'create-rule-for-update-test', 2345)
    response = handler(request, ())
    print(f"create response: {response}")
    assert response['Status'] == 'SUCCESS'

    # update the rule
    old_properties = {
        'Name': 'create-rule-for-update-test',
        'MetricName': 'create-rule-for-update-test-metric',
        'RateKey': 'IP',
        'RateLimit': 2345
    }
    updates = [
        {
            'Negated': False,
            'Type': 'IPMatch',
            'DataId': 'data-id-1'
        }
    ]

    request = Request('Update', 'test-update-with-new-predicate', 2345, 'IP', updates, old_properties)
    print(f"request: {request}")

    response = handler(request, ())
    print(f"update response: {response}")

    assert response['Status'] == 'SUCCESS'


@patch('botocore.client.BaseClient._make_api_call', mock_boto_calls)
def test_update_rule_with_existing_predicate():
    # create a rule
    request = Request('Create', 'create-rule-for-update-test', 2345)
    response = handler(request, ())
    print(f"create response: {response}")
    assert response['Status'] == 'SUCCESS'

    # update the rule
    old_properties = {
        'Name': 'create-rule-for-update-test',
        'MetricName': 'create-rule-for-update-test-metric',
        'RateKey': 'IP',
        'RateLimit': 2345,
        'MatchPredicates': [
            {
                'Negated': False,
                'Type': 'IPMatch',
                'DataId': 'data-id-1'
            }
        ]
    }
    updates = [
        {
            'Negated': True,
            'Type': 'ByteMatch',
            'DataId': 'data-id-1'
        }
    ]

    request = Request('Update', 'test-update-with-existing-predicate', 2345, 'IP', updates, old_properties)
    print(f"request: {request}")
    response = handler(request, ())
    print(f"update response: {response}")

    assert response['Status'] == 'SUCCESS'


@patch('botocore.client.BaseClient._make_api_call', mock_boto_calls)
def test_update_rule_mixed_predicate():
    # create a rule
    request = Request('Create', 'create-rule-for-update-test', 2345)
    response = handler(request, ())
    print(f"create response: {response}")
    assert response['Status'] == 'SUCCESS'

    # update the rule
    old_properties = {
        'Name': 'create-rule-for-update-test',
        'MetricName': 'create-rule-for-update-test-metric',
        'RateKey': 'IP',
        'RateLimit': 2345,
        'MatchPredicates': [
            {
                'Negated': False,
                'Type': 'IPMatch',
                'DataId': 'data-id-1'
            },
            {
                'Negated': False,
                'Type': 'IPMatch',
                'DataId': 'data-id-2'
            }
        ]
    }
    updates = [
        {
            'Negated': True,
            'Type': 'ByteMatch',
            'DataId': 'data-id-1'
        },
        {
            'Negated': False,
            'Type': 'RegexMatch',
            'DataId': 'data-id-3'
        }
    ]

    request = Request('Update', 'test-update-mixed', 2345, 'IP', updates, old_properties)
    print(f"request: {request}")
    response = handler(request, ())
    print(f"update response: {response}")

    assert response['Status'] == 'SUCCESS'


@patch('botocore.client.BaseClient._make_api_call', mock_boto_calls)
def test_update_rule_remove_predicate():
    # create a rule
    request = Request('Create', 'create-rule-for-update-test', 2345)
    response = handler(request, ())
    print(f"create response: {response}")
    assert response['Status'] == 'SUCCESS'

    # update the rule
    old_properties = {
        'Name': 'create-rule-for-update-test',
        'MetricName': 'create-rule-for-update-test-metric',
        'RateKey': 'IP',
        'RateLimit': 2345,
        'MatchPredicates': [
            {
                'Negated': False,
                'Type': 'IPMatch',
                'DataId': 'data-id-1'
            }
        ]
    }
    updates = []

    request = Request('Update', 'test-update-remove', 2345, 'IP', updates, old_properties)
    print(f"request: {request}")
    response = handler(request, ())
    print(f"update response: {response}")

    assert response['Status'] == 'SUCCESS'


@patch('botocore.client.BaseClient._make_api_call', mock_boto_calls)
def test_update_rule_missing_arguments_predicate():
    # create a rule
    request = Request('Create', 'create-rule-for-update-test', 2345)
    response = handler(request, ())
    print(f"create response: {response}")
    assert response['Status'] == 'SUCCESS'

    # update the rule
    old_properties = {
        'Name': 'create-rule-for-update-test',
        'MetricName': 'create-rule-for-update-test-metric',
        'RateKey': 'IP',
        'RateLimit': 2345
    }
    updates = [
        {
            'Type': 'ByteMatch',
            'DataId': 'data-id-1'
        }
    ]

    request = Request('Update', 'test-update-missing-arguments-predicate', 2345, 'IP', updates, old_properties)
    print(f"request: {request}")
    response = handler(request, ())
    print(f"update response: {response}")

    assert response['Status'] == 'FAILED'
    assert response['Reason'] == "Predicate {'Type': 'ByteMatch', 'DataId': 'data-id-1'} " \
                                 "is missing required fields: {'Negated'}"


@patch('botocore.client.BaseClient._make_api_call', mock_boto_calls)
def test_delete_rate_based_rule_predicate():
    old_properties = {
        'Name': 'create-rule-for-update-test',
        'MetricName': 'create-rule-for-update-test-metric',
        'RateKey': 'IP',
        'RateLimit': 2345,
        'MatchPredicates': [
            {
                'Negated': False,
                'Type': 'IPMatch',
                'DataId': 'data-id-1'
            }
        ]
    }

    request = Request('Delete', 'test-delete-rate-based-rule', 2345, 'IP', old_properties=old_properties)
    print(f"request: {request}")

    response = handler(request, ())
    print(f"delete response: {response}")

    assert response['Status'] == 'SUCCESS'


class Request(dict):

    def __init__(self, request_type, name, rate_limit, rate_key='IP',
                 updates=None, old_properties=None, physical_resource_id=None):
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

        if old_properties is not None:
            self['OldResourceProperties'] = old_properties

        if updates is not None:
            self['ResourceProperties']['Updates'] = updates

        if physical_resource_id is not None:
            self['PhysicalResourceId'] = physical_resource_id

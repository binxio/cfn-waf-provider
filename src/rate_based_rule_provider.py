from cfn_resource_provider import ResourceProvider
import boto3
import time
from botocore.exceptions import ClientError
import logging
import os

log = logging.getLogger()
log.setLevel(os.environ.get('LOG_LEVEL', 'DEBUG'))

client = boto3.client('waf')


class RateBasedRuleProvider(ResourceProvider):
    def __init__(self):
        super(RateBasedRuleProvider, self).__init__()
        self.request_schema = {
            'type': 'object',
            'required': ['Name', 'MetricName', 'RateKey', 'RateLimit'],
            'properties': {
                'Name': {'type': 'string'},
                'MetricName': {'type': 'string'},
                'RateKey': {'type': 'string'},
                'RateLimit': {'type': 'integer'},
                'MatchPredicates': {
                    'Negated': {'type': 'boolean'},
                    'Type': {'type': 'string',
                             'description': 'IPMatch | ByteMatch | SqlInjectionMatch | GeoMatch | SizeConstraint | '
                                            'XssMatch | RegexMatch'},
                    'DataId': {'type': 'string'}
                }
            }
        }

    def create(self):
        kwargs = self.properties.copy()

        try:
            kwargs.pop('ServiceToken', None)
            kwargs.pop('MatchPredicates', None)

            kwargs.update({'ChangeToken': client.get_change_token()['ChangeToken']})
            response = client.create_rate_based_rule(**kwargs)

            self.physical_resource_id = response['Rule']['RuleId']

            self.wait_on_status(response['ChangeToken'], current_retry=0)   # wait for the rule to finish creating

            print(f'properties_before_create: {self.properties}')

            if self.response['Status'] == 'SUCCESS':
                if 'MatchPredicates' in self.properties:   # check if the rule needs to be updated with predicate(s)
                    print('Predicate(s) detected in create request. Also updating the rule.')

                    update = {'RuleId': self.physical_resource_id}
                    update.update({'RateLimit': self.properties['RateLimit']})

                    predicates = []
                    for predicate in self.properties['MatchPredicates']:
                        predicates.append({
                            'Action': 'INSERT',
                            'Predicate': predicate
                        })
                    update.update({'Updates': predicates})

                    self.execute_update(update)

                    if self.response['Status'] == 'SUCCESS':
                        print('Create and update are done.')
                        self.success('Create and update are done.')
                    else:
                        print('Updating the created rule failed.')
                        self.fail('Updating the created rule failed.')
                else:
                    print('Create is done.')
                    self.success('Create is done.')
        except ClientError as error:
            self.physical_resource_id = 'failed-to-create'
            self.fail(f'{error}')

    def update(self):
        self.convert_properties(self.old_properties)    # also convert the old properties
        old_predicates = self.old_properties['MatchPredicates'] if 'MatchPredicates' in self.old_properties else {}
        print(f'old_predicates: {old_predicates}')
        print(f'new_predicates: {self.properties}')

        new_predicates = self.properties['MatchPredicates'] if 'MatchPredicates' in self.properties else {} # get new predicates from request

        update_request = self.create_update_request(old_predicates, new_predicates)
        self.execute_update(update_request)

    def delete(self):
        # Check for predicates, if so delete them first
        if 'MatchPredicates' in self.properties:
            update = {'RuleId': self.physical_resource_id}
            update.update({'RateLimit': self.properties['RateLimit']})

            predicates = []
            for predicate in self.properties['MatchPredicates']:
                predicates.append({
                    'Action': 'DELETE',
                    'Predicate': predicate
                })
            update.update({'Updates': predicates})
            self.execute_update(update, remove_all=True)

        # Perform the deletion of the rule
        try:
            delete_request = {'RuleId': self.physical_resource_id}
            delete_request.update({'ChangeToken': client.get_change_token()['ChangeToken']})
            response = client.delete_rate_based_rule(**delete_request)

            self.wait_on_status(response['ChangeToken'], current_retry=0)   # wait for the rule to finish deleting

            if self.response['Status'] == 'SUCCESS':
                print('Delete is done.')
                self.success('Delete is done.')
        except ClientError as error:
            if 'WAFNonexistentItemException' in error.response['__type']:
                self.success()
            else:
                self.fail(f'{error}')

    def create_update_request(self, old_predicates, new_predicates):
        def find_old_predicate(new_pred, old_preds):
            for old_pred in old_preds:
                if new_pred['DataId'] == old_pred['DataId']:
                    return old_pred
                else:
                    return None

        def missing_fields(kwargs):
            required_fields = ['Negated', 'Type', 'DataId']
            return set(required_fields) - set(kwargs)

        deletes = []
        inserts = []

        # check for each predicate if it already exists, if so delete it and insert a new one
        for new_predicate in new_predicates:
            missing = missing_fields(new_predicate)
            print(f'missing ==>> {missing}')
            if not missing:
                old_predicate = find_old_predicate(new_predicate, old_predicates)
                print(f'old_predicate ==>> {old_predicate}')
                old_predicates = [p for p in old_predicates if p != old_predicate]  # remove from predicate list
                if old_predicate is not None and new_predicate != old_predicate:
                    deletes.append({
                        'Action': 'DELETE',
                        'Predicate': old_predicate
                    })
                    inserts.append({
                        'Action': 'INSERT',
                        'Predicate': new_predicate
                    })
                elif old_predicate is None:
                    inserts.append({
                        'Action': 'INSERT',
                        'Predicate': new_predicate
                    })
            else:
                self.fail(f'Predicate {new_predicate} is missing required fields: {missing}')
                return

        # delete any predicates that are no longer present in the update request
        for old_predicate in old_predicates:
            deletes.append({
                'Action': 'DELETE',
                'Predicate': old_predicate
            })

        print(f'delete_set: {deletes}')
        print(f'insert_set: {inserts}')

        update_request = {'RuleId': self.physical_resource_id}
        update_request.update({'RateLimit': self.properties['RateLimit']})

        if deletes or inserts:
            merged_list = list(deletes + inserts)   # merge delete and insert set
            update_request.update({'Updates': merged_list})

        return update_request

    def execute_update(self, update_request, remove_all=False):
        try:
            update_request.update({'ChangeToken': client.get_change_token()['ChangeToken']})
            print(f'updates: {update_request}')
            response = client.update_rate_based_rule(**update_request)

            status = self.wait_on_status(response['ChangeToken'], current_retry=0)   # wait for the rule to finish updating

            return status
        except ClientError as error:
            if 'WAFNonexistentItemException' in error.response["__type"] and remove_all:
                self.success()
            else:
                self.fail(f'{error}')

    def wait_on_status(self, change_token, current_retry, interval=30, max_interval=30, max_retries=15):
        try:
            response = client.get_change_token_status(ChangeToken=change_token)

            if response['ChangeTokenStatus'] != 'INSYNC':
                if current_retry >= max_retries:
                    print(f'Max reties ({max_retries}) reached, something must have gone wrong. '
                          f"Current status: {response['ChangeTokenStatus']}.")
                    self.fail(f'Max retries ({max_retries}) reached, something must have gone wrong.')
                else:
                    print(f"Not done, current status is: {response['ChangeTokenStatus']}. "
                          f'Waiting {interval} seconds before retrying.')
                    time.sleep(interval)
                    self.wait_on_status(change_token,
                                               current_retry=current_retry + 1,
                                               interval=min(interval + interval, max_interval))
            else:
                self.success()
        except ClientError as error:
            self.physical_resource_id = 'failed-to-create'
            self.fail(f'{error}')

    def convert_property_types(self):
        self.convert_properties(self.properties)

    def convert_properties(self, properties):
        def convert(string):
            v = str(string)
            if v.lower() == 'true':
                return True
            elif v.lower() == 'false':
                return False
            elif check_int(v):
                return int(v)
            else:
                return v

        def check_int(i):
            try:
                int(i)
                return True
            except ValueError:
                return False

        if isinstance(properties, list):
            print(f'properties: {properties} is a list')
            for p in properties:
                self.convert_properties(p)
        else:
            for prop in properties:
                print(f'checking prop: {prop}')
                if isinstance(properties[prop], str):
                    print(f'properties[prop]: {properties[prop]} is a string')
                    properties[prop] = convert(properties[prop])
                elif iter(prop):
                    print(f'prop: {prop} is an iterable')
                    self.convert_properties(properties[prop])
                else:
                    print('Unknown type, passing...')
                    pass


provider = RateBasedRuleProvider()


def handler(request, context):
    return provider.handle(request, context)

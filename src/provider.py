import rate_based_rule_provider


def handler(request, context):
    if request['ResourceType'] == 'Custom::RateBasedRule':
        return rate_based_rule_provider.handler(request, context)
    else:
        print(f"Unknown resource type: {request['ResourceType']}")

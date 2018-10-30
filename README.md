# WAF Custom Provider with Rate-based Rule Support

The AWS [Web Application Firewall](https://aws.amazon.com/waf/faq/) (WAF) is a managed firewall service that supports a 
large variety of protection options in the form of rules. These rules should be linked to [web access control lists](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl.html) (ACLs) 
which in turn are attached to an Amazon Cloudfront or Application Load Balancer. 

*Note*: This provider was created for and is currently only tested for the CloudFront variant, the regional variant 
should also work for basic usage.


##  What is a Rate-based Rule in AWS WAF?
   
[Rate-based Rules](https://aws.amazon.com/blogs/aws/protect-web-sites-services-using-rate-based-rules-for-aws-waf/) are 
a new type of rule that can be configured for the AWS WAF. This feature allows you to specify the number of web requests that 
are allowed by a client IP in a trailing, continuously updated, 5 minute period. If an IP address breaches the configured 
limit, new requests will be blocked until the request rate falls below the configured threshold. Even better is the fact
that by default the rate-based rule will track and manage the 5-minute window for each IP address for you.


## Why do I need a custom resource provider?

While most WAF resources can be deployed using CloudFormation, rate-based rules are not supported and are currently only
creatable using the AWS Console or with API calls. As we consider it a best practice to deploy infrastructure as code 
we want to have this functionality available to us in CloudFormation. This custom resource provider does exactly that!

## How do I use it?

Creating a rate-based rule without any predicates does not have any prerequisites, however if you want to attach any 
predicates to the rule they have to be created before they can be attached to the rule. 

IMPORTANT: Due to the behavior of the WAF API actions only one rule should be in creation at a time, see 
[here](waf-api-behavior). The current workaround is to make each rate-based rule depend on the next using the 
```DependsOn:``` CloudFormation statement.

1. [Custom::RateBasedRule](syntax-yaml)
2. [AWS WAF Predicate(s)](https://docs.aws.amazon.com/waf/latest/APIReference/API_Predicate.html) (Optional)
    - [AWS::WAF::IPSet](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-waf-ipset.html)
    - [AWS::WAF::SizeConstraintSet](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-waf-sizeconstraintset.html)
    - [AWS::WAF::SqlInjectionMatchSet](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-waf-sqlinjectionmatchset.html)
    - [AWS::WAF::ByteMatchSet](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-waf-bytematchset.html)
    - [AWS::WAF::XssMatchSet](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-waf-xssmatchset.html)

If you have deployed your desired predicates you can add the [MatchPredicates](#syntax-yaml) section to rate-based 
rule's cloudformation template. MatchPredicates expects a list of predicate definitions such as the example below:

```yaml
MatchPredicates:
-
    Negated: False
    Type: XssMatch
    DataId: !Ref XssMatchSetPredicate
-
    Negated: True
    Type: IPMatch
    DataId: !ImportValue IPSetPredicate
```

*Note*: The predicates must be created/exist before the custom resource is created.

Checkout the sample rules in the [demo-stack.yaml](cloudformation/demo-stack.yaml) for more information.

## Syntax YAML

```yaml
Type: Custom::RateBasedRule
Properties:
  Name: string
  MetricName: string
  RateKey: string (Only valid value is IP)
  RateLimit: integer (>=2000)
  MatchPredicates:
  -
    Negated: True |False
    Type: IPMatch | ByteMatch | SqlInjectionMatch | GeoMatch | SizeConstraint | XssMatch | RegexMatch
    DataId: Predicate's physical ID
  ServiceToken: Arn of the custom resource provider lambda function
```

## Installation

To install this custom resource, type:

```sh
aws cloudformation create-stack \
	--capabilities CAPABILITY_IAM \
	--stack-name cfn-waf-provider \
	--template-body file://cloudformation/cfn-waf-provider.yaml 

aws cloudformation wait stack-create-complete  --stack-name cfn-waf-provider 
```

This CloudFormation template will use our pre-packaged provider from `s3://binxio-public-${AWS_REGION}/lambdas/cfn-waf-provider-0.2.0.zip`.


## Demo

To try out the Custom Resource type the following to deploy the demo:

```sh
aws cloudformation create-stack --stack-name cfn-waf-provider-predicates-demo \
	--template-body file://cloudformation/demo-predicates-stack.yaml \
aws cloudformation wait stack-create-complete  --stack-name cfn-waf-provider-predicates-demo
```

```sh
aws cloudformation create-stack --stack-name cfn-waf-provider-demo \
	--template-body file://cloudformation/demo-stack.yaml \
aws cloudformation wait stack-create-complete  --stack-name cfn-waf-provider-demo
```

This will deploy a cfn-waf-provider-predicates-demo stack containing several example predicates and a cfn-waf-provider-demo 
stack containing some examples of rate-based rules. Some with predicates and some without.


## WAF API Behavior

In order to create, update, or delete a rule we have to request a ChangeToken from WAF. We send this token with such a 
request, which allows the WAF to prevent conflicting requests from being submitted. However, once a change token is 
requested using the getChangeToken action it continues to return the same token until it is actually used in a create, 
update or delete request. For the custom provider this means that if at least two resources are created simultaneously 
they can potentially receive the same change token. The first to use the token succeeds while the others will receive a 
stale token error. However, the current behavior means that we have to either force sequential create, update and delete 
requests for rate-based rules using the ```DependsOn:``` CloudFormation statement or configure the lambda with max 
concurrency one. This does come with the downside that rule creation plus an update to add predicates can take up to 10 
minutes per rule. 

Another option is to request a new token whenever a conflict occurs, however, I do not like the idea of hoping that 
these conflicts don’t cascade to the point of “too many request timeouts” on the API. Lastly, one could also attempt to 
force synchronization during the token request and it being used, however, that seems like a poor design choice to me.
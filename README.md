# WAF Custom Provider with Rate-based Rule Support

The AWS Web Application Firewall (WAF) is a managed firewall service that supports a large variety of protection 
options in the form of rules. These rules are linked a web access control list (ACL) which in turn is attached to an 
Amazon Cloudfront or Application Load Balancer.


##  What is a Rate-based Rule in AWS WAF?
   
Rate-based Rules are a new type of Rule that can be configured in [AWS WAF](https://aws.amazon.com/waf/faq/). 
This feature allows you to specify the number of web requests that are allowed by a client IP in a trailing, 
continuously updated, 5 minute period. If an IP address breaches the configured limit, new requests will be 
blocked until the request rate falls below the configured threshold.


## Why do I need a custom resource provider?

While most WAF resources can be deployed using Cloudformation. Rate-based rules are not supported. Since we consider
it a best practice to deploy your infrastructure as code we want to have this functionality available to us. This
custom resource provider does exactly that!

## How do I use it?

Creating a rate-based rule without any predicates does not have any prerequisites, however if you want to attach any 
predicates to the rule you have to create them first. 

1. [Custom::RateBasedRule](syntax-yaml)
2. [AWS WAF Predicate(s)](https://docs.aws.amazon.com/waf/latest/APIReference/API_Predicate.html) (Optional)

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

Note: The predicates must be created/exist before the custom resource is created.

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
# WAF Custom Provider with Rate-based Rule Support

The AWS Web Application Firewall (WAF) is a managed firewall service which supports a large variety of protection 
options in the form of rules. These rules are linked a web access control ist (ACL) which in turn is attached to an 
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

As a prerequisite, you need to have the hosted zones for the domain names on your certificate in Route53. If you have that,
you can fully automate the provisioning of certificates, with the following resources:

1. [Custom::RateBasedRule](docs/Certificate.md) to request a certificate without waiting for it to be issued
3. [AWS::WAF::IPSet](docs/CertificateDNSRecord) which will obtain the DNS record for a domain name on the certificate.
3. [AWS::WAF::WebACL](docs/IssuedCertificate.md) which will activately wait until the certificate is issued.

Checkout the sample rules in [cloudformation/demo-stack.yaml](cloudformation/demo-stack.yaml).

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

To try out the Custom Resource type the following:

```sh
aws cloudformation create-stack --stack-name cfn-waf-provider-demo \
	--template-body file://cloudformation/demo-stack.yaml \
aws cloudformation wait stack-create-complete  --stack-name cfn-waf-provider-demo
```

This will deploy a stack containing some example rate-based rules. Some with predicates and some without.
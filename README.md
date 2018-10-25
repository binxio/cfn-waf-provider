# WAF Custom Provider with Rate-based Rule Support

The AWS Web Application Firewall (WAF) is a managed firewall service which supports a large variety of protection 
options in the form of rules. These rules are linked a web access control ist (ACL) which in turn is attached to an 
Amazon Cloudfront or Application Load Balancer.

 However one of the rule types that the WAF provides is not creatable using Cloudformation.




## How do I request certificates fully automatically?

As a prerequisite, you need to have the hosted zones for the domain names on your certificate in Route53. If you have that,
you can fully automate the provisioning of certificates, with the following resources:

1. [Custom::Certificate](docs/Certificate.md) to request a certificate without waiting for it to be issued
3. [Custom::CertificateDNSRecord](docs/CertificateDNSRecord) which will obtain the DNS record for a domain name on the certificate.
3. [Custom::IssuedCertificate](docs/IssuedCertificate.md) which will activately wait until the certificate is issued.
4. [AWS::Route53::ResourceRecordSet](https://docs.aws.amazon.com/Route53/latest/APIReference/API_ResourceRecordSet.html) to create the validation DNS record.

Checkout the sample in [cloudformation/demo-stack.yaml](cloudformation/demo-stack.yaml).

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
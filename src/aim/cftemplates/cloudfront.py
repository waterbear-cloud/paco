import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from aim.models.references import Reference
from io import StringIO
from enum import Enum
import base64


class CloudFront(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 aws_name,
                 app_id,
                 grp_id,
                 cloudfront_id,
                 cloudfront_config,
                 config_ref):

        # Super Init:
        aws_name='-'.join(["CloudFront", aws_name])
        super().__init__(aim_ctx,
                         account_ctx,
                         aws_region,
                         config_ref=config_ref,
                         aws_name=aws_name)


        self.set_parameter('LCEBSOptimized', asg_config.ebs_optimized)

        template_fmt = """
---
AWSTemplateFormatVersion: "2010-09-09"

Description: 'CloudFront Distribution'

Parameters:


Resources:

  Distribution:
    Type: "AWS::CloudFront::Distribution"
    Properties:
      DistributionConfig:
        Aliases:{0[domain_aliases]:s}
        DefaultCacheBehavior:
          AllowedMethods:{0[allowed_methods]:s}
          ForwardedValues:
            QueryString: true # http://docs.aws.amazon.com/cloudfront/latest/APIReference/API_ForwardedValues.html
            Cookies:
              Forward: all
            Headers:
              - "*"
          DefaultTTL: 0
          TargetOriginId: !Ref OriginId
          ViewerProtocolPolicy: !Ref ViewerProtocolPolicy
        DefaultRootObject: !Ref DefaultRootObject
        Enabled: true
        HttpVersion: http1.1
        Origins:{0[origins]:s}
        PriceClass: !Ref PriceClass
        ViewerCertificate:
          AcmCertificateArn: !Ref ViewerCertificate
          SslSupportMethod: !Ref SSLSupportedMethod
        WebACLId: !Ref WAFWebACL

Outputs:
  CloudFrontURL:
    Value: !GetAtt [ Cloudfront, DomainName ]

  CloudFrontId:
    Value: !Ref Cloudfront
"""

        self.set_template(template_fmt.format(template_table))
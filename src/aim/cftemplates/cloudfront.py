import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from aim.models.references import Reference, is_ref
from aim.utils import md5sum
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
                 cloudfront_config,
                 config_ref):

        # Super Init:
        aws_name='-'.join(["CloudFront", aws_name])
        super().__init__(aim_ctx,
                         account_ctx,
                         aws_region,
                         config_ref=config_ref,
                         aws_name=aws_name)

        template_fmt = """
---
AWSTemplateFormatVersion: "2010-09-09"

Description: 'CloudFront Distribution'

Parameters:

{0[parameters]:s}

Resources:

  Distribution:
    Type: "AWS::CloudFront::Distribution"
    Properties:
      DistributionConfig:
        Aliases:{0[domain_aliases]:s}
        Enabled: !Ref DistributionEnabled
        DefaultCacheBehavior:
          AllowedMethods:{0[allowed_methods]:s}
          ForwardedValues:
            QueryString: true # http://docs.aws.amazon.com/cloudfront/latest/APIReference/API_ForwardedValues.html
            Cookies:
              Forward: all
            Headers:
              - "*"
          DefaultTTL: !Ref DefaultTTL
          TargetOriginId: !Ref DefaultTargetOriginId
          ViewerProtocolPolicy: !Ref ViewerProtocolPolicy
        # DefaultRootObject: !Ref DefaultRootObject
        HttpVersion: http1.1
        Origins:{0[origins]:s}
        PriceClass: !Ref PriceClass
        ViewerCertificate:
          AcmCertificateArn: !Ref ViewerCertificate
          SslSupportMethod: !Ref ViewerCertSSLSupportedMethod
          MinimumProtocolVersion: !Ref ViewerCertMinimumProtocolVersion
{0[custom_error_responses]:s}
{0[webacl_id]:s}

{0[aliases_record_sets]:s}

Outputs:
  CloudFrontURL:
    Value: !GetAtt Distribution.DomainName

  CloudFrontId:
    Value: !Ref Distribution
"""
        template_table = {
            'parameters': None,
            'domain_aliases': None,
            'allowed_methods': None,
            'origins': None
        }
        # CloudFormation YAML Init
        parameters_yaml = ""

        # Globals

        # ---------------------------------------------------------------------
        # DistributionEnabled
        parameters_yaml += self.gen_parameter(
          param_type='String',
          name='DistributionEnabled',
          description='Boolean indicating whether the distribution is enabled or not',
          value=cloudfront_config.enabled
        )
        # Price Class
        parameters_yaml += self.gen_parameter(
          param_type='String',
          name='PriceClass',
          description='CloudFront Price Class',
          value='PriceClass_'+cloudfront_config.price_class
        )
        # Default Target Origin ID
        parameters_yaml += self.gen_parameter(
          param_type='String',
          name='DefaultTargetOriginId',
          description='Default Target Origin Id',
          value=cloudfront_config.default_cache_behavior.target_origin
        )
         # Default Target Origin ID
        parameters_yaml += self.gen_parameter(
          param_type='String',
          name='ViewerProtocolPolicy',
          description='Default Viewer Protocol Policy',
          value=cloudfront_config.default_cache_behavior.viewer_protocol_policy
        )
        # Default TTL
        parameters_yaml += self.gen_parameter(
          param_type='String',
          name='DefaultTTL',
          description='Default TTL',
          value=cloudfront_config.default_cache_behavior.default_ttl
        )
        # Viewer Certificate
        # The certificate needs to be in us-east-1 which is automatically
        # created in the app_engine with an aim reference of:
        #
        viewer_cert_ref = 'aim.ref '+self.config_ref+'.viewer_certificate.arn'
        parameters_yaml += self.gen_parameter(
          param_type='String',
          name='ViewerCertificate',
          description='SSL Viewer Certificate',
          value=viewer_cert_ref
        )
        # Viewer Certificate SSL Supported Method
        parameters_yaml += self.gen_parameter(
          param_type='String',
          name='ViewerCertSSLSupportedMethod',
          description='SSL Viewer Certificate SSL Supported Method',
          value=cloudfront_config.viewer_certificate.ssl_supported_method
        )
        # Viewer Certificate SSL Supported Method
        parameters_yaml += self.gen_parameter(
          param_type='String',
          name='ViewerCertMinimumProtocolVersion',
          description='SSL Viewer Certificate Minimum Protocol Version',
          value=cloudfront_config.viewer_certificate.minimum_protocol_version
        )
        # WAF Web Acl Id
        webacl_id_yaml = ""
        if cloudfront_config.webacl_id != None:
            webacl_id_yaml = "        WebACLId: !Ref WAFWebACLId"
            parameters_yaml += self.gen_parameter(
              param_type='String',
              name='WebAclId',
              description='WAF Web Acl ID',
              value=cloudfront_config.webacl_id
            )

        # ---------------------------------------------------------------------
        # Domain Aliases
        aliases_fmt = "\n          - !Ref {0[domain_name_param]:s}"
        aliases_table = {
          'domain_name': None
        }
        aliases_record_sets_fmt = """
  RecordSet{0[cname_id]:s}:
    Type: AWS::Route53::RecordSet
    DependsOn:
      - Distribution
    Properties:
      HostedZoneId: !Ref {0[zone_param_name]:s}
      Name: !Ref {0[domain_name_param]:s}
      Type: A
      AliasTarget:
        DNSName: !GetAtt Distribution.DomainName
        HostedZoneId: Z2FDTNDATAQYW2
"""
        aliases_record_sets_table = {
            'cname_id': None,
            'zone_param_name': None,
            'domain_name_param': None
        }
        domain_aliases_yaml = ""
        aliases_record_sets_yaml = ""
        for alias in cloudfront_config.domain_aliases:
            alias_hash = md5sum(str_data=alias.domain_name)
            # DomainAlias
            domain_name_param = 'DomainAlias' + alias_hash
            parameters_yaml += self.gen_parameter(
                param_type='String',
                name=domain_name_param,
                description='Domain Alias CNAME',
                value=alias.domain_name)
            aliases_table['domain_name_param'] = domain_name_param
            domain_aliases_yaml += aliases_fmt.format(aliases_table)
            # RecordSet
            zone_param_name = 'AliasHostedZoneId' + alias_hash
            parameters_yaml += self.gen_parameter(
                param_type='String',
                name=zone_param_name,
                description='Domain Alias Hosted Zone Id',
                value=alias.hosted_zone+'.id')
            aliases_table['domain_name'] = zone_param_name
            aliases_record_sets_table['cname_id'] = alias_hash
            aliases_record_sets_table['domain_name_param'] = domain_name_param
            aliases_record_sets_table['zone_param_name'] = zone_param_name
            aliases_record_sets_yaml += aliases_record_sets_fmt.format(aliases_record_sets_table)


        # ---------------------------------------------------------------------
        # Allowed Methods
        allowed_methods_yaml = ""
        for method in cloudfront_config.default_cache_behavior.allowed_methods:
            allowed_methods_yaml += "\n            - {}".format(method)

        # ---------------------------------------------------------------------
        # Origins
        origin_fmt = """
          - Id: {0[id]:s}
            DomainName: {0[domain_name]:s}
            CustomOriginConfig:
              HTTPPort: {0[http_port]:d}
              HTTPSPort: {0[https_port]:d}
              OriginKeepaliveTimeout: {0[keepalive_timeout]:d}
              OriginProtocolPolicy: {0[protocol_policy]:s}
              OriginReadTimeout: {0[read_timeout]:d}
              OriginSSLProtocols:{0[ssl_protocols]:s}
"""
        origin_table = {
            'id': None,
            'domain_name': None,
            'http_port': None,
            'https_port': None,
            'keepalive_timeout': None,
            'protocol_policy': None,
            'read_timeout': None,
            'ssl_protocols': None
        }
        origins_yaml = ""
        for origin_name, origin in cloudfront_config.origins.items():
            domain_hash = md5sum(str_data=origin.domain_name)
            param_name = 'OriginDomain' + domain_hash
            parameters_yaml += self.gen_parameter(
                param_type='String',
                name=param_name,
                description='Origin Domain Name',
                value=origin.domain_name
            )
            origin_table['id'] = origin_name
            origin_table['domain_name'] = '!Ref ' + param_name
            origin_table['http_port'] = origin.custom_origin_config.http_port
            origin_table['https_port'] = origin.custom_origin_config.https_port
            origin_table['keepalive_timeout'] = origin.custom_origin_config.keepalive_timeout
            origin_table['protocol_policy'] = origin.custom_origin_config.protocol_policy
            origin_table['read_timeout'] = origin.custom_origin_config.read_timeout
            origin_table['ssl_protocols'] = ""
            for ssl_protocol in origin.custom_origin_config.ssl_protocols:
                origin_table['ssl_protocols'] += "\n                - %s" % ssl_protocol
            origins_yaml += origin_fmt.format(origin_table)
        # ---------------------------------------------------------------------
        # Custom Error Responses
        error_resp_fmt = """        CustomErrorResponses:
          - ErrorCachingMinTTL: {0[error_caching_min_ttl]:d}
            ErrorCode: {0[error_code]:d}
            ResponseCode: {0[response_code]:d}
            ResponsePagePath: {0[response_page_path]:s}
"""
        error_resp_table = {
            'error_caching_min_ttl': None,
            'error_code': None,
            'response_code': None,
            'response_page_path': None
        }
        custom_error_responses_yaml = ""
        for error_resp in cloudfront_config.custom_error_responses:
            for key in error_resp_table.keys():
                value = getattr(error_resp, key)
                error_resp_table[key] = value
            custom_error_responses_yaml += error_resp_fmt.format(error_resp_table)

        # ---------------------------------------------------------------------

        template_table['parameters'] = parameters_yaml
        template_table['domain_aliases'] = domain_aliases_yaml
        template_table['allowed_methods'] = allowed_methods_yaml
        template_table['origins'] = origins_yaml
        template_table['aliases_record_sets'] = aliases_record_sets_yaml
        template_table['custom_error_responses'] = custom_error_responses_yaml
        template_table['webacl_id'] = webacl_id_yaml


        self.set_template(template_fmt.format(template_table))
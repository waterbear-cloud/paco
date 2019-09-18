import os
from aim.cftemplates.cftemplates import CFTemplate

from aim.models.references import Reference, is_ref, resolve_ref
from aim.utils import md5sum
from io import StringIO
from enum import Enum
import base64


class CloudFront(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 aws_name,
                 app_id,
                 grp_id,
                 cloudfront_config,
                 config_ref,
                 stack_order):

        # Super Init:
        aws_name='-'.join(["CloudFront", aws_name])
        super().__init__(aim_ctx,
                         account_ctx,
                         aws_region,
                         enabled=cloudfront_config.is_enabled(),
                         config_ref=config_ref,
                         aws_name=aws_name,
                         stack_group=stack_group,
                         stack_tags=stack_tags,
                         stack_order=stack_order)

        origin_access_id_enabled = False

        template_fmt = """
---
AWSTemplateFormatVersion: "2010-09-09"

Description: 'CloudFront Distribution'

Parameters:

{0[parameters]:s}

  OriginAccessIdentityEnabled:
    Type: String
    Description: "Boolean indicating whether an Access Identify will be created."
    AllowedValues:
      - true
      - false

Conditions:
  OriginAccessIdentityIsEnabled: !Equals [ OriginAccessIdentityEnabled, 'true' ]
  DistributionIsEnabled: !Equals [ !Ref DistributionEnabled, 'true' ]

Resources:

  CloudFrontOriginAccessIdentity:
    Type: AWS::CloudFront::CloudFrontOriginAccessIdentity
    Condition: OriginAccessIdentityIsEnabled
    Properties:
      CloudFrontOriginAccessIdentityConfig:
        Comment: !Sub '${{AWS::StackName}}'

  Distribution:
    Type: "AWS::CloudFront::Distribution"
    Properties:
      DistributionConfig:
        Aliases: {0[domain_aliases]:s}
        Enabled: !Ref DistributionEnabled
        DefaultCacheBehavior:
          AllowedMethods:{0[allowed_methods]:s}
          {0[forwarded_values]:s}
          DefaultTTL: !Ref DefaultTTL
          TargetOriginId: !Ref DefaultTargetOriginId
          ViewerProtocolPolicy: !Ref ViewerProtocolPolicy
        DefaultRootObject: !Ref DefaultRootObject
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

  CloudFrontOriginAccessIdentity:
    Condition: OriginAccessIdentityIsEnabled
    Value: !Ref CloudFrontOriginAccessIdentity
"""
        template_table = {
            'parameters': None,
            'domain_aliases': None,
            'allowed_methods': None,
            'origins': None,
            'aliases_record_sets': None,
            'custom_error_responses': None,
            'webacl_id': None,
            'forwarded_values': None
        }
        # CloudFormation YAML Init
        parameters_yaml = ""
        origins_yaml = ""

        # Globals

        # ---------------------------------------------------------------------
        # DistributionEnabled
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='DistributionEnabled',
          description='Boolean indicating whether the distribution is enabled or not',
          value=cloudfront_config.is_enabled()
        )
        # Price Class
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='PriceClass',
          description='CloudFront Price Class',
          value='PriceClass_'+cloudfront_config.price_class
        )
        # Default Target Origin ID
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='DefaultTargetOriginId',
          description='Default Target Origin Id',
          value=cloudfront_config.default_cache_behavior.target_origin
        )
         # Default Target Origin ID
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='ViewerProtocolPolicy',
          description='Default Viewer Protocol Policy',
          value=cloudfront_config.default_cache_behavior.viewer_protocol_policy
        )
        # Default TTL
        parameters_yaml += self.create_cfn_parameter(
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
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='ViewerCertificate',
          description='SSL Viewer Certificate',
          value=viewer_cert_ref
        )
        # Viewer Certificate SSL Supported Method
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='ViewerCertSSLSupportedMethod',
          description='SSL Viewer Certificate SSL Supported Method',
          value=cloudfront_config.viewer_certificate.ssl_supported_method
        )
        # Viewer Certificate SSL Supported Method
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='ViewerCertMinimumProtocolVersion',
          description='SSL Viewer Certificate Minimum Protocol Version',
          value=cloudfront_config.viewer_certificate.minimum_protocol_version
        )
        # WAF Web Acl Id
        webacl_id_yaml = ""
        if cloudfront_config.webacl_id != None:
            webacl_id_yaml = "        WebACLId: !Ref WAFWebACLId"
            parameters_yaml += self.create_cfn_parameter(
              param_type='String',
              name='WebAclId',
              description='WAF Web Acl ID',
              value=cloudfront_config.webacl_id
            )
        # Default Root Object: example: index.html
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='DefaultRootObject',
          description='The default path to load from the origin.',
          value=cloudfront_config.default_root_object
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
    Condition: DistributionIsEnabled
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
            parameters_yaml += self.create_cfn_parameter(
                param_type='String',
                name=domain_name_param,
                description='Domain Alias CNAME',
                value=alias.domain_name)
            aliases_table['domain_name_param'] = domain_name_param
            domain_aliases_yaml += aliases_fmt.format(aliases_table)
            # RecordSet
            zone_param_name = 'AliasHostedZoneId' + alias_hash
            parameters_yaml += self.create_cfn_parameter(
                param_type='String',
                name=zone_param_name,
                description='Domain Alias Hosted Zone Id',
                value=alias.hosted_zone+'.id')
            aliases_table['domain_name'] = zone_param_name
            aliases_record_sets_table['cname_id'] = alias_hash
            aliases_record_sets_table['domain_name_param'] = domain_name_param
            aliases_record_sets_table['zone_param_name'] = zone_param_name
            if cloudfront_config.is_dns_enabled() == True:
                aliases_record_sets_yaml += aliases_record_sets_fmt.format(aliases_record_sets_table)


        # ---------------------------------------------------------------------
        # Allowed Methods
        allowed_methods_yaml = ""
        for method in cloudfront_config.default_cache_behavior.allowed_methods:
            allowed_methods_yaml += "\n            - {}".format(method)

        # ---------------------------------------------------------------------
        # Forwarded Value
        forwarded_values_fmt = """
          ForwardedValues:
            QueryString: {0[query_string]:s}
            Cookies: {0[cookies]:s}
            {0[headers]:s}
"""
        forwarded_values_table = {
            'query_string': None,
            'cookies': None,
            'headers': None
        }
        forward_values_config = cloudfront_config.default_cache_behavior.forwarded_values
        # Query String
        forwarded_values_table['query_string'] = str(forward_values_config.query_string)
        # Cookies
        if cloudfront_config.s3_origin_exists() == True:
            forwarded_values_table['cookies'] =        "\n              Forward: none"
        else:
            forwarded_values_table['cookies'] =        "\n              Forward: " + forward_values_config.cookies.forward
            if len(forward_values_config.cookies.white_listed_names) > 0:
                forwarded_values_table['cookies'] +=   "\n              WhiteListedNames:  "
                for white_listed_name in forward_values_config.cookies.white_listed_names:
                  forwarded_values_table['cookies'] += "\n                - " + white_listed_name
        # Header
        forwarded_values_table['headers'] = ""
        if cloudfront_config.s3_origin_exists() == False:
            forwarded_values_table['headers'] = "Headers: "
            for header in cloudfront_config.default_cache_behavior.forwarded_values.headers:
                forwarded_values_table['headers'] +=    "\n              - '{}'".format(header)

        forwarded_values_yaml = forwarded_values_fmt.format(forwarded_values_table)


        # ---------------------------------------------------------------------
        # Origins
        origin_fmt = """
          - Id: {0[id]:s}
            DomainName: {0[domain_name]:s}
            {0[s3_origin_config]:s}
            {0[custom_origin_config]:s}
"""
        s3_origin_config_fmt = """
            S3OriginConfig:
              OriginAccessIdentity: {0[origin_access_id]:s}
"""
        s3_origin_access_id_fmt = """
                !Sub
                  - 'origin-access-identity/cloudfront/${{OriginAccessId}}'
                  - {{ OriginAccessId: {0[sub_origin_access_id]:s} }}
"""
        custom_origin_config_fmt = """
            CustomOriginConfig:
              {0[http_port]:s}
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
            'ssl_protocols': None,
            's3_origin_config': None
        }
        if cloudfront_config.s3_origin_exists() == True:
            self.set_parameter('OriginAccessIdentityEnabled', 'true')
        else:
            self.set_parameter('OriginAccessIdentityEnabled', 'false')
        for origin_name, origin in cloudfront_config.origins.items():
            if origin.s3_bucket != None:
                domain_hash = md5sum(str_data=origin.s3_bucket)
                origin_domain_name = self.aim_ctx.get_ref(origin.s3_bucket+'.url')
            else:
                domain_hash = md5sum(str_data=origin.domain_name)
                origin_domain_name = origin.domain_name
            param_name = 'OriginDomain' + domain_hash
            parameters_yaml += self.create_cfn_parameter(
                param_type='String',
                name=param_name,
                description='Origin Domain Name',
                value=origin_domain_name
            )
            origin_table['id'] = origin_name
            origin_table['domain_name'] = '!Ref ' + param_name
            origin_table['s3_origin_config'] = ''
            origin_table['custom_origin_config'] = ''
            if origin.s3_bucket != None:
                s3_config = self.aim_ctx.get_ref(origin.s3_bucket)
            if origin.s3_bucket == None:
                origin_table['http_port'] = ''
                if origin.custom_origin_config.http_port != None:
                  origin_table['http_port'] = 'HTTPPort: '+str(origin.custom_origin_config.http_port)
                origin_table['https_port'] = origin.custom_origin_config.https_port
                origin_table['keepalive_timeout'] = origin.custom_origin_config.keepalive_timeout
                origin_table['protocol_policy'] = origin.custom_origin_config.protocol_policy
                origin_table['read_timeout'] = origin.custom_origin_config.read_timeout
                origin_table['ssl_protocols'] = ""
                for ssl_protocol in origin.custom_origin_config.ssl_protocols:
                    origin_table['ssl_protocols'] += "\n                - " + ssl_protocol
                origin_table['custom_origin_config'] += custom_origin_config_fmt.format(origin_table)
            else:
                # Origin Access Identify
                if s3_config.cloudfront_origin == False:
                    origin_table['origin_access_id'] = "''"
                else:
                    origin_access_id_enabled = True
                    param_name = "OriginAccessIdentiy"+domain_hash
                    origin_table['sub_origin_access_id'] = "!Ref "+param_name
                    access_id_ref = origin.s3_bucket+'.origin_id'
                    parameters_yaml += self.create_cfn_parameter(
                      param_type='String',
                      name=param_name,
                      description='Origin Access Identity',
                      value=access_id_ref
                    )
                    origin_table['origin_access_id'] = s3_origin_access_id_fmt.format(origin_table)
                origin_table['s3_origin_config'] = s3_origin_config_fmt.format(origin_table)
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
        if domain_aliases_yaml == "":
            domain_aliases_yaml = "!Ref 'AWS::NoValue'"
        template_table['domain_aliases'] = domain_aliases_yaml
        template_table['allowed_methods'] = allowed_methods_yaml
        template_table['origins'] = origins_yaml
        template_table['aliases_record_sets'] = aliases_record_sets_yaml
        template_table['custom_error_responses'] = custom_error_responses_yaml
        template_table['webacl_id'] = webacl_id_yaml
        template_table['forwarded_values'] = forwarded_values_yaml

        self.set_template(template_fmt.format(template_table))
        if origin_access_id_enabled:
          self.stack.wait_on_delete = True
import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from io import StringIO
from enum import Enum


class S3(CFTemplate):
    def __init__(self,
                aim_ctx,
                account_ctx,
                aws_region,
                bucket_context,
                bucket_policy_only,
                config_ref):
        aws_name = 'S3'
        if bucket_context['group_id'] != None:
            aws_name = '-'.join([aws_name, bucket_context['group_id']])
        aws_name = '-'.join([aws_name, bucket_context['id']])
        if bucket_policy_only == True:
            aws_name += '-policy'

        super().__init__(aim_ctx,
                         account_ctx,
                         aws_region,
                         config_ref=config_ref,
                         aws_name=aws_name,
                         iam_capabilities=["CAPABILITY_NAMED_IAM"])

        self.s3_context_id = config_ref
        self.bucket_context = bucket_context

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'S3 Buckets'

#Parameters:
#{0[parameters_yaml]:s}

Resources:
{0[resources_yaml]:s}

{0[outputs_yaml]:s}
"""
        template_table = {
            'parameters_yaml': "",
            'resources_yaml': "",
            'outputs_yaml': ""
        }

        s3_bucket_fmt = """
  {0[cf_resource_name_prefix]:s}Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: {0[bucket_name]:s}
    DeletionPolicy: Retain
"""

        cloudfront_origin_fmt = """
  CloudFrontOriginAccessIdentity:
    Type: AWS::CloudFront::CloudFrontOriginAccessIdentity
    Properties:
      CloudFrontOriginAccessIdentityConfig:
        Comment: '{0[access_id_description]:s}'

  CloudFrontBucketPolicy:
    Type: AWS::S3::BucketPolicy
    DependsOn:
      - CloudFrontOriginAccessIdentity
      - {0[cf_resource_name_prefix]:s}Bucket
    Properties:
      Bucket: {0[bucket_name]:s}
      PolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              CanonicalUser: !GetAtt CloudFrontOriginAccessIdentity.S3CanonicalUserId
            Action:
              - s3:GetObject
            Resource:
              - arn:aws:s3:::{0[bucket_name]:s}/*
"""
        cloudfront_origin_table = {
            'access_id_description': None,
            'cf_resource_name_prefix': None,
            'bucket_name': None
        }

        s3_policy_fmt = """
  {0[cf_resource_name_prefix]:s}BucketPolicy:
  {0[cf_policy_depends_on]:s}
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: {0[bucket_name]:s}
      PolicyDocument:
        Statement: {0[policy_statements]:s}
"""
        s3_policy_depends_on_fmt = """  DependsOn:
      - {0[cf_resource_name_prefix]:s}Bucket"""

        s3_policy_table = {
            'cf_resource_name_prefix': "",
            'bucket_name' : "",
            'policy_statements': "",
            'cf_policy_depends_on': ""
        }

        s3_policy_statement_fmt = """
          - Action:{0[action_list]:s}
            Effect: {0[effect]:s}
            Principal:
{0[principal]:s}
            Resource: {0[resource_list]:s}
            {0[condition]:s}
"""
        s3_policy_statement_table = {
            'action_list': "",
            'effect': "",
            'principal': "",
            'resource_list': "",
            'condition': "",
            }

        s3_bucket_outputs_fmt = """
  {0[cf_resource_name_prefix]:s}BucketName:
    Value: !Ref {0[cf_resource_name_prefix]:s}Bucket
"""

        s3_bucket_table = {
            'bucket_name': None,
            'cf_resource_name_prefix': None
        }

        cf_list_item = """
              - '{0}'"""

        cf_principal_list_item = """
                - '{0}'"""

        parameters_yaml = ""
        resources_yaml = ""
        outputs_yaml = ""

        s3_ctl = self.aim_ctx.get_controller('S3')

        s3_bucket_table.clear()
        bucket_config = bucket_context['config']
        s3_bucket_table['bucket_name'] = s3_ctl.get_bucket_name(self.s3_context_id)
        cf_name_prefix = self.gen_cf_logical_name(self.bucket_context['id'], '_')
        s3_bucket_table['cf_resource_name_prefix'] = cf_name_prefix

        if bucket_policy_only == False:
            # parameters_yaml += s3_bucket_params_fmt.format(s3_bucket_table)
            resources_yaml += s3_bucket_fmt.format(s3_bucket_table)

        if bucket_config.cloudfront_origin == True:
            cloudfront_origin_table['bucket_name'] = s3_bucket_table['bucket_name']
            cloudfront_origin_table['cf_resource_name_prefix'] = cf_name_prefix
            cloudfront_origin_table['access_id_description'] = self.s3_context_id
            resources_yaml += cloudfront_origin_fmt.format(cloudfront_origin_table)
            outputs_yaml += self.gen_output('CloudFrontOriginAccessIdentity', '!Ref CloudFrontOriginAccessIdentity')
            self.register_stack_output_config(config_ref+'.origin_id', 'CloudFrontOriginAccessIdentity')
        elif len(bucket_config.policy) > 0:
            # Bucket Policy
            if bucket_policy_only == False:
                s3_policy_table['cf_policy_depends_on'] = s3_policy_depends_on_fmt.format(s3_bucket_table)

            s3_policy_table['cf_resource_name_prefix'] = cf_name_prefix
            s3_policy_table['bucket_name'] = s3_bucket_table['bucket_name']
            s3_policy_table['policy_statements'] = ""
            # Statement
            for policy_statement in bucket_config.policy:
                if policy_statement.processed == True:
                    continue
                s3_policy_statement_table['action_list'] = ""
                s3_policy_statement_table['principal'] = ""
                s3_policy_statement_table['effect'] = ""
                s3_policy_statement_table['resource_list'] = ""
                # Action
                for action in policy_statement.action:
                    s3_policy_statement_table['action_list'] += cf_list_item.format(action)
                # Effect
                s3_policy_statement_table['effect'] = policy_statement.effect

                # Principal - principal field
                if policy_statement.principal != None and len(policy_statement.principal) > 0:
                    for key, value in policy_statement.principal.items():
                        s3_policy_statement_table['principal'] = "              {}:".format(key)
                        # can be a string or list
                        if type(value) == type(list()):
                            for item in value:
                                s3_policy_statement_table['principal'] += cf_principal_list_item.format(item)
                        else:
                            s3_policy_statement_table['principal'] += cf_principal_list_item.format(value)

                # Principal - aws field
                elif policy_statement.aws != None and len(policy_statement.aws) > 0:
                    s3_policy_statement_table['principal'] = "              AWS:"
                    for principal in policy_statement.aws:
                        s3_policy_statement_table['principal'] += cf_principal_list_item.format(principal)

                if policy_statement.condition != {}:
                    padding = "              "
                    condition = "Condition:\n"
                    for key, value in policy_statement.condition.items():
                        condition += padding + "  {}:\n".format(key)
                        for sub_key, sub_value in value.items():
                            if type(sub_value) == type(list()):
                                condition += padding + "    '{}':\n".format(sub_key)
                                for item in sub_value:
                                    condition += padding + "      - '{}'\n".format(item)
                            else:
                                condition += padding + "    '{}': '{}'\n".format(sub_key, sub_value)
                    s3_policy_statement_table['condition'] = condition

                # Resource
                bucket_arn = s3_ctl.get_bucket_arn(self.s3_context_id)
                if policy_statement.resource_suffix and len(policy_statement.resource_suffix) > 0:
                    for res_suffix in policy_statement.resource_suffix:
                        resource_arn = bucket_arn + res_suffix
                        s3_policy_statement_table['resource_list'] += cf_list_item.format(resource_arn)
                else:
                    s3_policy_statement_table['resource_list'] = cf_list_item.format(bucket_arn)
                s3_policy_table['policy_statements'] += s3_policy_statement_fmt.format(s3_policy_statement_table)
            resources_yaml += s3_policy_fmt.format(s3_policy_table)
        if bucket_policy_only == False:
            outputs_yaml += s3_bucket_outputs_fmt.format(s3_bucket_table)
            self.register_stack_output_config(config_ref+'.name', cf_name_prefix+'BucketName')

        template_table['parameters_yaml'] = parameters_yaml
        template_table['resources_yaml'] = resources_yaml
        if outputs_yaml != '':
            outputs_yaml = "Outputs:\n"+outputs_yaml
        template_table['outputs_yaml'] = outputs_yaml

        self.set_template(template_fmt.format(template_table))

    def delete(self):
        s3_ctl = self.aim_ctx.get_controller('S3')
        s3_ctl.empty_bucket(self.bucket_context['ref'])
        super().delete()

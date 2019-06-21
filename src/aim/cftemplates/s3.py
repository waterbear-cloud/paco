import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from io import StringIO
from enum import Enum


class S3(CFTemplate):
    def __init__(self, aim_ctx, account_ctx, s3_config, app_id, group_id, s3_context_id, config_ref):
        aws_name = group_id

        super().__init__(aim_ctx,
                         account_ctx,
                         config_ref=config_ref,
                         aws_name=aws_name,
                         iam_capabilities=["CAPABILITY_NAMED_IAM"])

        self.s3_context_id = s3_context_id
        self.s3_config = s3_config
        self.app_id = app_id
        self.group_id = group_id

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'S3 Buckets'

#Parameters:
#{0[parameters_yaml]:s}

Resources:
{0[resources_yaml]:s}

Outputs:
{0[outputs_yaml]:s}
"""
        template_table = {
            'parameters_yaml': "",
            'resources_yaml': "",
            'outputs_yaml': ""
        }

#        s3_params_fmt ="""
#  {0[?_name]:s}:
#    Type: String
#    Description: 'The path associated with the {0[role_path_param_name]:s} IAM Role'
#"""

        s3_bucket_fmt = """
  {0[cf_resource_name_prefix]:s}Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: {0[bucket_name]:s}
    DeletionPolicy: Retain
"""

        s3_policy_fmt = """
  {0[cf_resource_name_prefix]:s}BucketPolicy:
    DependsOn:
      - {0[cf_resource_name_prefix]:s}Bucket
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: {0[bucket_name]:s}
      PolicyDocument:
        Statement: {0[policy_statements]:s}
"""
        s3_policy_table = {
            'cf_resource_name_prefix': "",
            'bucket_name' : "",
            'policy_statements': ""
        }

        s3_policy_statement_fmt = """
          - Action:{0[action_list]:s}
            Effect: {0[effect]:s}
            Principal:
{0[principal]:s}
            Resource: {0[resource_list]:s}
"""
        s3_policy_statement_table = {
            'action_list': "",
            'effect': "",
            'principal': "",
            'resource_list': ""
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

        roles_yaml = ""
        for bucket_id in s3_config.get_bucket_ids(self.app_id, self.group_id):
            s3_bucket_table.clear()
            bucket_name = s3_config.get_bucket_name(self.app_id, self.group_id, bucket_id)
            s3_bucket_table['bucket_name'] = bucket_name
            s3_bucket_table['cf_resource_name_prefix'] = self.gen_cf_logical_name(bucket_id, '_')

            # parameters_yaml += s3_bucket_params_fmt.format(s3_bucket_table)
            resources_yaml += s3_bucket_fmt.format(s3_bucket_table)

            # Bucket Policy
            if s3_config.has_bucket_policy(self.app_id, self.group_id, bucket_id):
                s3_policy_table['cf_resource_name_prefix'] = s3_bucket_table['cf_resource_name_prefix']
                s3_policy_table['bucket_name'] = bucket_name
                s3_policy_table['policy_statements'] = ""
                # Statement
                for policy_statement in s3_config.get_bucket_policy_list(self.app_id, self.group_id, bucket_id):
                    s3_policy_statement_table['action_list'] = ""
                    s3_policy_statement_table['principal'] = ""
                    s3_policy_statement_table['effect'] = ""
                    s3_policy_statement_table['resource_list'] = ""
                    # Action
                    for action in policy_statement.action:
                        s3_policy_statement_table['action_list'] += cf_list_item.format(action)
                    # Effict
                    s3_policy_statement_table['effect'] = policy_statement.effect
                    # Principal
                    if policy_statement.aws != None and len(policy_statement.aws) > 0:
                        s3_policy_statement_table['principal'] = "              AWS:"
                        for principal in policy_statement.aws:
                            s3_policy_statement_table['principal'] += cf_principal_list_item.format(principal)

                    # Resource
                    bucket_arn = "arn:aws:s3:::{0}".format(bucket_name)
                    if policy_statement.resource_suffix and len(policy_statement.resource_suffix) > 0:
                        for res_suffix in policy_statement.resource_suffix:
                            resource_arn = bucket_arn + res_suffix
                            s3_policy_statement_table['resource_list'] += cf_list_item.format(resource_arn)
                    else:
                        s3_policy_statement_table['resource_list'] = cf_list_item.format(bucket_arn)
                    s3_policy_table['policy_statements'] += s3_policy_statement_fmt.format(s3_policy_statement_table)
                resources_yaml += s3_policy_fmt.format(s3_policy_table)
            outputs_yaml += s3_bucket_outputs_fmt.format(s3_bucket_table)

        template_table['parameters_yaml'] = parameters_yaml
        template_table['resources_yaml'] = resources_yaml
        template_table['outputs_yaml'] = outputs_yaml
        self.set_template(template_fmt.format(template_table))

    def validate(self):
        #self.aim_ctx.log("Validating S3 Template")
        super().validate()


    def get_outputs_key_from_ref(self, aim_ref):
        ref_dict = self.aim_ctx.parse_ref(aim_ref)
        ref_parts = ref_dict['ref_parts']
        last_idx = len(ref_parts)-1
        output_key = None
        if ref_parts[last_idx] == "name":
            output_key = self.gen_cf_logical_name(ref_parts[last_idx-1], '_') + "BucketName"

        return output_key

    def delete(self):
        s3_ctl = self.aim_ctx.get_controller('S3')
        s3_ctl.init(self.s3_context_id)
        for bucket_id in self.s3_config.get_bucket_ids(self.app_id, self.group_id):
            s3_ctl.empty_bucket(self.app_id, self.group_id, bucket_id)
        super().delete()

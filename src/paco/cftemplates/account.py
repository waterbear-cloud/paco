import os
from paco.cftemplates.cftemplates import CFTemplate
from io import StringIO
from enum import Enum

class Account(CFTemplate):
    def __init__(self,
                 paco_ctx,
                 account_ctx,
                 stack_group,
                 stack_tags,
                 account_id,
                 account_config,
                 account_config_ref):

        #paco_ctx.log("Segment CF Template init")
        self.account_config = account_config
        self.account_id = account_id
        # Super
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region=account_config.region,
            config_ref=account_config_ref,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name(self.account_id)

        # Define the Template
        template = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Waterbear Cloud AWS Account'

#------------------------------------------------------------------------------
  # IAM Users
{0[iam_users]:s}

#Outputs:

"""
        template_table = {
          'iam_users': None
        }

        iam_user_template = """
  WaterbearCloudAdminUser{0[id]:d}:
    Type: AWS::IAM::User
    Properties:
      UserName: {0[username]:s}
"""
        iam_user_table = {
            'id': 0,
            'username': None
        }

        iam_users_yaml = ""
        if self.account_config.admin_iam_users:
            iam_users_yaml += """
Resources:
    """
            iam_user_table['id'] = 0
            for iam_user_id in self.account_config.admin_iam_users:
                iam_user_config = self.account_config.admin_iam_users[iam_user_id]
                if iam_user_config.username == self.paco_ctx.project['credentials'].master_admin_iam_username:
                    continue
                iam_user_table['username'] = iam_user_config.username
                iam_users_yaml += iam_user_template.format(iam_user_table)
                iam_user_table['id'] += 1

        template_table['iam_users'] = iam_users_yaml
        template_yaml = template.format(template_table)
        self.set_template(template_yaml)

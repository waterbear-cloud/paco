import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from io import StringIO
from enum import Enum

class Account(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 account_id,
                 account_config,
                 account_config_ref):

        #aim_ctx.log("Segment CF Template init")
        self.account_config = account_config
        self.account_id = account_id
        # Super
        super().__init__(aim_ctx,
                         account_ctx,
                         aws_account=None,
                         config_ref=account_config_ref,
                         aws_name=self.account_id,
                         iam_capabilities=["CAPABILITY_NAMED_IAM"])

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
                iam_user_table['username'] = iam_user_config.username
                iam_users_yaml += iam_user_template.format(iam_user_table)
                iam_user_table['id'] += 1

        template_table['iam_users'] = iam_users_yaml
        template_yaml = template.format(template_table)
        self.set_template(template_yaml)

    def validate(self):
        #self.aim_ctx.log("Validating Segment Template")
        super().validate()

    def get_outputs_key_from_ref(self, aim_ref):
        return None

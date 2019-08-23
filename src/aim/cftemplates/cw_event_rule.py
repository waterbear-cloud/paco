import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from io import StringIO
from enum import Enum
import base64
from aim.models import vocabulary


class CWEventRule(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 event_description,
                 schedule_expression,
                 target_arn,
                 target_id,
                 config_ref):

        #aim_ctx.log("CLoudWatch Alarms CF Template init")
        # Super Init:
        aws_name='-'.join(['EventRule'])
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=config_ref,
            aws_name=aws_name,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags
        )

        # Initialize Parameters
        self.set_parameter('ScheduleExpression', schedule_expression)
        self.set_parameter('EventTargetArn', target_arn)
        self.set_parameter('EventTargetId', target_id)
        self.set_parameter('EventDescription', event_description)

        # TOOD: Template needs Scale in/out policies

        # Define the Template
        template_yaml = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'CloudWatch EventRule'

Parameters:

  # https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html
  ScheduleExpression:
    Description: "The scheduling expression that determines when and how often the rule runs."
    Type: String

  EventTargetArn:
    Description: "The resource that CloudWatch Events routes events to and invokes when the rule is triggered."
    Type: String

  EventTargetId:
    Description: "The ID of the target. It can include alphanumeric characters, periods (.), hyphens (-), and underscores (_)."
    Type: String

  EventDescription:
    Description: "A description of the EventRule"
    Type: String

Resources:

  TargetInvocationRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: "Allow"
            Principal:
              Service:
                - events.amazonaws.com
            Action:
              - "sts:AssumeRole"
      Policies:
        - PolicyName: TargetInvocation
          PolicyDocument:
            Version: 2012-10-17
            Statement:
                - Sid: TargetInvocation
                  Effect: Allow
                  Action:
                    - lambda:InvokeFunction
                  Resource:
                    - !Ref EventTargetArn

  EventRule:
    Type: AWS::Events::Rule
    Properties:
      # If you specify a name, you can't perform updates that require replacement of this resource.
      # Name: Do not use to allow replacement of resource.
      Description: !Ref EventDescription
      ScheduleExpression: !Ref ScheduleExpression
      State: "ENABLED"
      Targets:
        - Arn: !Ref EventTargetArn
          Id: !Ref EventTargetId

Outputs:

  EventRuleId:
    Value: !Ref EventRule

  EventRuleArn:
    Value: !GetAtt EventRule.Arn
"""
        self.register_stack_output_config(config_ref+'.id', 'EventRuleId')
        self.register_stack_output_config(config_ref+'.arn', 'EventRuleArn')

        self.set_template(template_yaml)

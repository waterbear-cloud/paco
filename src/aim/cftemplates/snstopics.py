"""
CloudFormation template for SNS Topics
"""

from aim.cftemplates.cftemplates import CFTemplate


class SNSTopics(CFTemplate):
    """
    CloudFormation template for SNS Topics
    """
    def __init__(
        self,
        aim_ctx,
        account_ctx,
        aws_region,
        aws_name,
        config,
        res_config_ref
    ):
        aws_name='-'.join([aws_name, 'SNSTopics'])
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=res_config_ref,
            aws_name=aws_name
        )
        self.config = config

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'SNS Topics'

Resources:

{0[topics]:s}

Outputs:

{0[outputs]:s}
"""
        template_table = {
          'topics': None,
          'outputs': None,
        }
        output_fmt = """
  SNSTopic{0[name]:s}:
    Value: !Ref Topic{0[name]:s}
"""

        topic_fmt = """
  Topic{0[name]:s}:
    Type: AWS::SNS::Topic
    Properties:
{0[display_name]:s}
        Subscription:
{0[subscription]:s}

"""

        topics_yaml = ""
        outputs_yaml = ""
        for topic in config.values():
            if topic.title:
                display_name = "        DisplayName: '{}'".format(topic.title)
            else:
                display_name = ""
            subscription = ''
            for member in topic.values():
                subscription += "            - Endpoint: {}\n              Protocol: {}\n".format(
                    member.name, member.protocol
                )
            topic_table = {
                'name': self.normalize_resource_name(topic.name),
                'display_name': display_name,
                'subscription': subscription
            }
            topics_yaml += topic_fmt.format(topic_table)
            outputs_yaml += output_fmt.format(topic_table)
            output_ref = '.'.join(['groups', topic.name])
            self.register_stack_output_config(output_ref, 'SNSTopic' + self.normalize_resource_name(topic.name))

        template_table['topics'] = topics_yaml
        template_table['outputs'] = outputs_yaml
        self.set_template(template_fmt.format(template_table))

    def validate(self):
        super().validate()


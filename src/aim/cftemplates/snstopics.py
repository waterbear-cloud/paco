"""
CloudFormation template for SNS Topics
"""

from aim.cftemplates.cftemplates import CFTemplate
from aim.models import references
from aim.models.references import Reference


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

{0[parameters]:s}

Resources:

{0[topics]:s}

Outputs:

{0[outputs]:s}
"""
        template_table = {
          'parameters': "",
          'topics': "",
          'outputs': ""
        }
        output_fmt = """
  SNSTopic{0[name]:s}:
    Value: !Ref Topic{0[name]:s}
"""

        topic_fmt = """
  Topic{0[name]:s}:
    Type: AWS::SNS::Topic
    {0[properties]:s}
      # Important: If you specify a TopicName, updates cannot be performed that require
      # replacement of this resource.
      # TopicName: !Ref AWS::NoValue{0[display_name]:s}
{0[subscription]:s}

"""

        topic_table = {
            'name': None,
            'properties': None,
            'display_name': None,
            'subscription': None
        }

        parameters_yaml = ""
        topics_yaml = ""
        outputs_yaml = ""
        for topic in self.config:
            topic_table['name'] = self.normalize_resource_name(topic.name)
            topic_table['display_name'] = ""
            topic_table['subscription'] = ""
            topic_table['properties'] = ""
            if topic.display_name != None or len(topic.subscriptions) > 0:
                topic_table['properties'] = "Properties:\n"
            if topic.display_name:
                topic_table['display_name'] = "\n      DisplayName: '{}'".format(topic.display_name)

            if len(topic.subscriptions) > 0:
                topic_table['subscription'] += "      Subscription:\n"
            for subscription in topic.subscriptions:
                endpoint = ""
                if references.is_ref(subscription.endpoint):
                    param_name = 'Endpoint%s' % topic_table['name']
                    parameters_yaml += self.gen_parameter('String', param_name, 'SNSTopic Endpoint value.')
                    self.set_parameter(param_name, subscription.endpoint)
                    endpoint = "!Ref %s" % param_name
                else:
                    endpoint = subscription.endpoint
                #if subscription.endpoint.is_ref()
                topic_table['subscription'] += "        - Endpoint: {}\n          Protocol: {}\n".format(
                    endpoint, subscription.protocol
                )

            topics_yaml += topic_fmt.format(topic_table)
            outputs_yaml += output_fmt.format(topic_table)
            output_ref = '.'.join(['groups', topic.name])
            self.register_stack_output_config(output_ref, 'SNSTopic' + self.normalize_resource_name(topic.name))

        if parameters_yaml != "":
            template_table['parameters'] = "Parameters:\n"
        template_table['parameters'] += parameters_yaml
        template_table['topics'] = topics_yaml
        template_table['outputs'] = outputs_yaml
        self.set_template(template_fmt.format(template_table))

    def validate(self):
        super().validate()

    def get_outputs_key_from_ref(self, ref):
        ref = Reference(ref)
        return "SNSTopic"+ref.last_part
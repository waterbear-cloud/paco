"""
CloudFormation template for SNS Topics
"""

import troposphere
import troposphere.sns
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
        stack_group,
        stack_tags,
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
            aws_name=aws_name,
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.config = config

        # Troposphere Template Initialization
        template = troposphere.Template(
            Description = 'SNS Topics',
        )
        template.set_version()
        template.add_resource(
            troposphere.cloudformation.WaitConditionHandle(title="DummyResource")
        )

        # Topic Resources and Outputs
        any_topic_enabled = False
        for topic in self.config:
            if not topic.is_enabled():
                continue
            any_topic_enabled = True
            topic_logical_id = self.create_cfn_logical_id(topic.name)

            # Do not specify a TopicName, as then updates cannot be performed that require
            # replacement of this resource.
            cfn_export_dict = {}
            if topic.display_name:
                cfn_export_dict['DisplayName'] = topic.display_name

            # Subscriptions
            if len(topic.subscriptions) > 0:
                cfn_export_dict['Subscription'] = []
            for subscription in topic.subscriptions:
                sub_dict = {}
                if references.is_ref(subscription.endpoint):
                    param_name = 'Endpoint{}'.format(topic_logical_id)
                    parameter = self.create_cfn_parameter(
                        param_type = 'String',
                        name = param_name,
                        description = 'SNSTopic Endpoint value',
                        value = subscription.endpoint,
                        use_troposphere = True
                    )
                    template.add_parameter(parameter)
                    endpoint = parameter
                else:
                    endpoint = subscription.endpoint
                sub_dict['Endpoint'] = endpoint
                sub_dict['Protocol'] = subscription.protocol
                cfn_export_dict['Subscription'].append(sub_dict)

            topic_resource = troposphere.sns.Topic.from_dict(
                'Topic' + topic_logical_id,
                cfn_export_dict
            )
            template.add_resource(topic_resource)

            # Topic Outputs
            output_ref = '.'.join([res_config_ref, topic.name])
            topic_output_arn = troposphere.Output(
                'SNSTopicArn' + topic_logical_id,
                Value=troposphere.Ref(topic_resource)
            )
            template.add_output(topic_output_arn)
            self.register_stack_output_config(output_ref + '.arn', 'SNSTopicArn' + topic_logical_id)
            topic_output_name = troposphere.Output(
                'SNSTopicName' + topic_logical_id,
                Value=troposphere.GetAtt(topic_resource, "TopicName")
            )
            template.add_output(topic_output_name)
            self.register_stack_output_config(output_ref + '.name', 'SNSTopicName' + topic_logical_id)

        self.enabled = any_topic_enabled

        # Generate the Template
        self.set_template(template.to_yaml())

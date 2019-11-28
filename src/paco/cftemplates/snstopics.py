"""
CloudFormation template for SNS Topics
"""

import awacs.sns
import troposphere
import troposphere.sns
from paco.cftemplates.cftemplates import CFTemplate
from paco.models import references
from paco.models.locations import get_parent_by_interface
from paco.models.references import Reference
from awacs.aws import Allow, Policy, Statement, Principal, Condition, StringEquals

class SNSTopics(CFTemplate):
    """
    CloudFormation template for SNS Topics
    """
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        grp_id,
        res_id,
        config,
        res_config_ref
    ):
        enabled_topics = False
        for topic in config:
            if topic.is_enabled():
                enabled_topics = True

        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            config_ref=res_config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags,
            enabled=enabled_topics,
        )
        self.set_aws_name('SNSTopics', grp_id, res_id)
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
        topics_ref_cross_list = []
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
            if topic.cross_account_access:
                topics_ref_cross_list.append(troposphere.Ref(topic_resource))
            topic.topic_resource = topic_resource
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


        # Cross-account access policy
        if len(topics_ref_cross_list) > 0:
            account_id_list = [
                account.account_id for account in self.paco_ctx.project.accounts.values()
            ]
            topic_policy_resource = troposphere.sns.TopicPolicy(
                'TopicPolicyCrossAccountPacoProject',
                Topics = topics_ref_cross_list,
                PolicyDocument = Policy(
                    Version = '2012-10-17',
                    Id = "CrossAccountPublish",
                    Statement=[
                        Statement(
                            Effect = Allow,
                            Principal = Principal("AWS", "*"),
                            Action = [ awacs.sns.Publish ],
                            Resource = topics_ref_cross_list,
                            Condition = Condition(
                                StringEquals({
                                    'AWS:SourceOwner': account_id_list,
                                })
                            )
                        )
                    ]
                )
            )
            template.add_resource(topic_policy_resource)

        self.enabled = any_topic_enabled

        # Generate the Template
        self.set_template(template.to_yaml())

"""
Template for SNS Topics and Subscriptions
"""

from paco.cftemplates.cftemplates import StackTemplate
from paco.models import references
from paco.models import schemas
from paco.models.locations import get_parent_by_interface
from awacs.aws import Allow, Policy, Statement, Principal, Condition, StringEquals
import awacs.sns
import json
import troposphere
import troposphere.sns


class SNS(StackTemplate):
    """
SNS Topics and Subscriptions
    """
    def __init__(
        self,
        stack,
        paco_ctx,
        grp_id=None,
        topics=None,
    ):
        enabled_topics = False
        config = stack.resource
        # this template is used as both SNSTopics by global resources and a
        # single SNSTopic for an application resource.
        if topics == None:
            if grp_id == None:
                topics = [stack.resource]
                enabled_topics = stack.resource.is_enabled()
            else:
                topics = config.values()
                for topic in topics:
                    if topic.is_enabled():
                        enabled_topics = True
        else:
            if len(topics) > 0:
                enabled_topics = True

        super().__init__(
            stack,
            paco_ctx,
            enabled=enabled_topics,
        )

        if grp_id == None:
            self.set_aws_name('SNS', self.resource_group_name, self.resource_name)
        else:
            self.set_aws_name('SNS', grp_id)

        # Troposphere Template Initialization
        self.init_template('SNS Topics and Subscriptions')
        template = self.template

        # Topic Resources and Outputs
        topics_ref_cross_list = []
        for topic in topics:
            if not topic.is_enabled():
                continue
            topic_logical_id = self.create_cfn_logical_id(topic.name)

            # Do not specify a TopicName, as then updates cannot be performed that require
            # replacement of this resource.
            cfn_export_dict = {}
            if topic.display_name:
                cfn_export_dict['DisplayName'] = topic.display_name

            # Topic Resource
            topic_resource = troposphere.sns.Topic.from_dict(
                'Topic' + topic_logical_id,
                cfn_export_dict
            )
            if topic.cross_account_access:
                topics_ref_cross_list.append(troposphere.Ref(topic_resource))
            topic.topic_resource = topic_resource
            template.add_resource(topic_resource)

            # Subscriptions
            idx = 0
            for subscription in topic.subscriptions:
                sub_dict = {
                    'TopicArn': troposphere.Ref(topic_resource)
                }
                if references.is_ref(subscription.endpoint):
                    param_name = f'Endpoint{topic_logical_id}{idx}'
                    parameter = self.create_cfn_parameter(
                        param_type = 'String',
                        name = param_name,
                        description = 'Subscription Endpoint',
                        value = subscription.endpoint,
                    )
                    endpoint = parameter
                else:
                    endpoint = subscription.endpoint
                sub_dict['Endpoint'] = endpoint
                sub_dict['Protocol'] = subscription.protocol
                if subscription.filter_policy:
                    sub_dict['FilterPolicy'] = json.loads(subscription.filter_policy)
                subscription_logical_id = f"Subscription{topic_logical_id}{idx}"
                sub_resource = troposphere.sns.SubscriptionResource.from_dict(
                    subscription_logical_id,
                    sub_dict
                )
                template.add_resource(sub_resource)
                idx += 1

            # Topic Outputs
            if grp_id == None:
                output_ref = stack.resource.paco_ref_parts
            else:
                output_ref = '.'.join([stack.resource.paco_ref_parts, topic.name])
            self.create_output(
                title='SNSTopicArn' + topic_logical_id,
                value=troposphere.Ref(topic_resource),
                ref=f'{output_ref}.arn'
            )
            self.create_output(
                title='SNSTopicName' + topic_logical_id,
                value=troposphere.GetAtt(topic_resource, "TopicName"),
                ref=f'{output_ref}.name',
            )

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

"""
CloudFormation template for SNS Topics
"""

import awacs.sns
import troposphere
import troposphere.sns
from paco.cftemplates.cftemplates import StackTemplate
from paco.models import references
from paco.models import schemas
from paco.models.locations import get_parent_by_interface
from awacs.aws import Allow, Policy, Statement, Principal, Condition, StringEquals


class SNSTopics(StackTemplate):
    """
    CloudFormation template for SNS Topics
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
            self.set_aws_name('SNSTopics', self.resource_group_name, self.resource_name)
        else:
            self.set_aws_name('SNSTopics', grp_id)

        # Troposphere Template Initialization
        self.init_template('SNS Topics')
        template = self.template

        # Topic Resources and Outputs
        topics_ref_cross_list = []
        topic_policy_cache = []
        for topic in topics:
            if not topic.is_enabled():
                continue
            statement_list = []
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
                    )
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

            topic.topic_resource = topic_resource
            template.add_resource(topic_resource)

            if topic.codestar_notification_access:
                statement = Statement(
                    Effect = Allow,
                    Sid = 'CodeStarNotificationAccess',
                    Principal = Principal("Service", 'codestar-notifications.amazonaws.com'),
                    Action = [ awacs.sns.Publish ],
                    Resource = [troposphere.Ref(topic_resource)],
                )
                statement_list.append(statement)

            if topic.events_bridge_notification_access:
                statement = Statement(
                    Effect = Allow,
                    Sid = 'EventBridgeNotificationAccess',
                    Principal = Principal("Service", 'events.amazonaws.com'),
                    Action = [ awacs.sns.Publish ],
                    Resource = [troposphere.Ref(topic_resource)],
                )
                statement_list.append(statement)

            # Add CloudWatch service
            statement = Statement(
                Effect = Allow,
                Sid = 'CloudWatchService',
                Principal = Principal("Service", 'cloudwatch.amazonaws.com'),
                Action = [ awacs.sns.Publish ],
                Resource = [troposphere.Ref(topic_resource)],
            )
            statement_list.append(statement)

            if topic.cross_account_access:
                account_id_list = [
                    account.account_id for account in self.paco_ctx.project.accounts.values()
                ]
                for account_id in account_id_list:
                    if account_id in topic_policy_cache:
                        continue
                    topic_policy_cache.append(account_id)
                    statement = Statement(
                        Effect = Allow,
                        Sid = self.create_cfn_logical_id_join(account_id),
                        Principal = Principal("AWS", f'arn:aws:iam::{account_id}:root'),
                        Action = [ awacs.sns.Publish, awacs.sns.Subscribe ],
                        Resource = [ troposphere.Ref(topic_resource) ],
                    )
                    statement_list.append(statement)

            if len(statement_list) > 0:
                topic_policy_resource = troposphere.sns.TopicPolicy(
                    f'Paco{topic_logical_id}TopicPolicy',
                    Topics = [troposphere.Ref(topic_resource)],
                    PolicyDocument = Policy(
                        Version = '2012-10-17',
                        Id = "PacoSNSTopicPolicy",
                        Statement=statement_list
                    )
                )
                template.add_resource(topic_policy_resource)

            # Topic Outputs
            if grp_id == None:
                output_ref = stack.resource.paco_ref_parts
            else:
                output_ref = '.'.join([stack.resource.paco_ref_parts, topic.name])
            self.create_output(
                title='SNSTopicArn' + topic_logical_id,
                value=troposphere.Ref(topic_resource),
                ref=output_ref + '.arn'
            )
            self.create_output(
                title='SNSTopicName' + topic_logical_id,
                value=troposphere.GetAtt(topic_resource, "TopicName"),
                ref=output_ref + '.name',
            )
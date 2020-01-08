import awacs.s3
import os
import troposphere
import troposphere.cloudfront
import troposphere.s3
from paco.cftemplates.cftemplates import CFTemplate
from paco.models import schemas
from awacs.aws import Action, Allow, Statement, Policy, Principal, Condition, StringEquals
from io import StringIO
from enum import Enum


class S3(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        stack_hooks,
        bucket_context,
        bucket_policy_only,
        config_ref,
        change_protected
    ):
        bucket = bucket_context['config']

        # Application Group
        aws_name_list = []
        if bucket_context['group_id'] != None:
            aws_name_list.append(bucket_context['group_id'])

        # Bucket Name
        if schemas.IResource.providedBy(bucket.__parent__) == True:
            aws_name_list.extend([bucket.__parent__.name, bucket.name])
            cfn_logical_id_prefix = self.create_cfn_logical_id_join([bucket.__parent__.name, bucket.name ], True)
        else:
            aws_name_list.append(bucket.name)
            cfn_logical_id_prefix = self.create_cfn_logical_id_join([bucket.name ], True)

        # Policy
        if bucket_policy_only == True:
            aws_name_list.append('policy')

        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=bucket_context['config'].is_enabled(),
            config_ref=config_ref,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags,
            stack_hooks=stack_hooks,
            change_protected=change_protected
        )
        self.set_aws_name('S3', aws_name_list)
        self.s3_context_id = config_ref
        self.bucket_context = bucket_context
        s3_ctl = self.paco_ctx.get_controller('S3')
        bucket_name = s3_ctl.get_bucket_name(self.s3_context_id)

        # Init Troposphere template
        self.init_template(bucket.title_or_name)
        template = self.template

        # Resources
        if bucket_policy_only == False:
            s3_logical_id = cfn_logical_id_prefix + 'Bucket'
            cfn_export_dict = bucket.cfn_export_dict
            cfn_export_dict['BucketName'] = bucket_name

            # notification configuration
            if hasattr(bucket, 'notifications'):
                cfn_export_dict['NotificationConfiguration'] = {}
                if hasattr(bucket.notifications, 'lambdas'):
                    lambda_notifs = []
                    params = {}
                    for lambda_notif in bucket.notifications.lambdas:
                        param_name = self.create_cfn_logical_id('LambdaNotif' + lambda_notif.function[9:])
                        if param_name not in params:
                            lambda_arn_param = self.create_cfn_parameter(
                                name = param_name,
                                param_type = 'String',
                                description = 'Lambda ARN parameter.',
                                value = lambda_notif.function + '.arn',
                                use_troposphere = True
                            )
                            params[param_name] = lambda_arn_param
                            template.add_parameter(lambda_arn_param)
                        lambda_notifs.append({
                            'Event': lambda_notif.event,
                            'Function': troposphere.Ref(param_name)
                        })
                    cfn_export_dict['NotificationConfiguration']["LambdaConfigurations"] = lambda_notifs

            s3_resource = troposphere.s3.Bucket.from_dict(s3_logical_id, cfn_export_dict)
            s3_resource.DeletionPolicy = 'Retain' # We always retain. Bucket cleanup is handled by Stack hooks.
            template.add_resource(s3_resource)
            bucket_name_output_id = s3_logical_id + 'Name'
            template.add_output(
                troposphere.Output(
                    bucket_name_output_id,
                    Value=troposphere.Ref(s3_resource)
                )
            )
            self.register_stack_output_config(config_ref + '.name', bucket_name_output_id)

        # Bucket Policy
        policy_statements = []
        if bucket.cloudfront_origin == True:
            # CloudFront OriginAccessIdentity resource
            cloudfront_origin_resource = troposphere.cloudfront.CloudFrontOriginAccessIdentity.from_dict(
                'CloudFrontOriginAccessIdentity',
                {'CloudFrontOriginAccessIdentityConfig': {'Comment': self.s3_context_id}},
            )
            template.add_resource(cloudfront_origin_resource)

            policy_statements.append(
                Statement(
                    Effect = Allow,
                    Principal = Principal('CanonicalUser',troposphere.GetAtt('CloudFrontOriginAccessIdentity','S3CanonicalUserId')),
                    Action = [awacs.s3.GetObject],
                    Resource = ['arn:aws:s3:::{}/*'.format(bucket_name)],
                )
            )

            # S3 BucketPolicy resource
            #policy = Policy(
            #    Version='2012-10-17',
            #    Statement=[
            #        Statement(
            #            Effect = Allow,
            #            Principal = Principal('CanonicalUser',troposphere.GetAtt('CloudFrontOriginAccessIdentity','S3CanonicalUserId')),
            #            Action = [awacs.s3.GetObject],
            #            Resource = ['arn:aws:s3:::{}/*'.format(bucket_name)],
            #        )
            #    ]
            #)
            #bucket_policy_resource = troposphere.s3.BucketPolicy(
            #    'CloudFrontBucketPolicy',
            #    Bucket = bucket_name,
            #    PolicyDocument = policy,
            #)
            #bucket_policy_resource.DependsOn = [
            #    'CloudFrontOriginAccessIdentity',
            #    s3_logical_id
            #]
            #template.add_resource(bucket_policy_resource)

            # Output CloudFrontOriginAccessIdentity
            template.add_output(
                troposphere.Output(
                    'CloudFrontOriginAccessIdentity',
                    Value=troposphere.Ref(cloudfront_origin_resource)
                )
            )
            self.register_stack_output_config(config_ref + '.origin_id', 'CloudFrontOriginAccessIdentity')

        if len(bucket.policy) > 0:
            # Bucket Policy
            # ToDo: allow mixing CloudFront Origin policies and other bucket policies together

            # Statement
            for policy_statement in bucket.policy:
                # XXX: Disabled: Bucket policies are overwritten when updated with a new stack.
                #                This means we want all of the policies previously provisioned.
                #if policy_statement.processed == True:
                #    continue
                statement_dict = {
                    'Effect': policy_statement.effect,
                    'Action': [
                        Action(*action.split(':')) for action in policy_statement.action
                    ],
                }

                # Principal
                if policy_statement.principal != None and len(policy_statement.principal) > 0:
                    # ToDo: awacs only allows one type of Principal ... is there a use-case where
                    # multiple principal types are needed?
                    for key, value in policy_statement.principal.items():
                        statement_dict['Principal'] = Principal(key, value)
                elif policy_statement.aws != None and len(policy_statement.aws) > 0:
                    statement_dict['Principal'] = Principal('AWS', policy_statement.aws)

                # Condition
                if policy_statement.condition != {}:
                    # ToDo: support all conditions!
                    # currently only invoked by ctl_cloudtrail.py
                    conditions = []
                    for condition_key, condition_value in policy_statement.condition.items():
                        if condition_key == 'StringEquals':
                            conditions.append(StringEquals(condition_value))
                        else:
                            raise StackException(
                                PacoErrorCode.Unknown,
                                message="Only StringEquals is a supported condition (*fix-me!*). Bucket name: {}".format(bucket_name)
                            )
                    statement_dict['Condition'] = Condition(conditions)

                # Resource
                bucket_arn = s3_ctl.get_bucket_arn(self.s3_context_id)
                if policy_statement.resource_suffix and len(policy_statement.resource_suffix) > 0:
                    statement_dict['Resource'] = [
                        bucket_arn + res_suffix
                        for res_suffix in policy_statement.resource_suffix
                    ]
                else:
                    statement_dict['Resource'] = [bucket_arn]

                policy_statements.append(
                    Statement(**statement_dict)
                )
        if len(policy_statements) > 0:
            bucket_policy_resource = troposphere.s3.BucketPolicy(
                cfn_logical_id_prefix + 'BucketPolicy',
                template = template,
                Bucket = bucket_name,
                PolicyDocument = Policy(
                    Version = '2012-10-17',
                    Statement = policy_statements,
                )
            )

            depends_on = []
            if bucket_policy_only == False:
                depends_on.append(s3_resource)
            if bucket.cloudfront_origin == True:
                depends_on.append('CloudFrontOriginAccessIdentity')
            bucket_policy_resource.DependsOn = depends_on

        # Generate the Template
        self.set_template(template.to_yaml())


    def delete(self):
        s3_ctl = self.paco_ctx.get_controller('S3')
        s3_ctl.empty_bucket(self.bucket_context['ref'])
        super().delete()

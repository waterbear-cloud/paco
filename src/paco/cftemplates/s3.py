import awacs.s3
import troposphere
import troposphere.cloudfront
import troposphere.s3
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.cftemplates.cftemplates import StackTemplate
from paco.models import schemas
from awacs.aws import *

def create_policy_statments(policies, s3bucket_arn_param=None, s3bucket_arn=None):
    policy_statements = []
    for policy_statement in policies:
        statement_dict = {
            'Effect': policy_statement.effect,
            'Action': [
                Action(*action.split(':')) for action in policy_statement.action
            ],
        }

        # Sid
        if policy_statement.sid != None and len(policy_statement.sid) > 0:
            statement_dict['Sid'] = policy_statement.sid

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
            conditions = []
            for condition_key, condition_value in policy_statement.condition.items():
                # Conditions can be simple:
                #   StringEquals
                # Or prefixed with ForAnyValue or ForAllValues
                #   ForAnyValue:StringEquals
                condition_key = condition_key.replace(':', '')
                condition_class = globals()[condition_key]
                conditions.append(condition_class(condition_value))

            statement_dict['Condition'] = Condition(conditions)

        # Resource
        # S3BucketPolicy uses Parameters
        if s3bucket_arn_param != None:
            if policy_statement.resource_suffix and len(policy_statement.resource_suffix) > 0:
                statement_dict['Resource'] = []
                for res_suffix in policy_statement.resource_suffix:
                    if res_suffix == '':
                        statement_dict['Resource'].append(
                            troposphere.Ref(s3bucket_arn_param)
                        )
                    else:
                        statement_dict['Resource'].append(
                            troposphere.Join(
                                '',
                                [troposphere.Ref(s3bucket_arn_param), res_suffix]
                            )
                        )
            else:
                statement_dict['Resource'] = [troposphere.Ref(s3bucket_arn_param)]
        # S3Bucket uses embdedded strings
        else:
            if policy_statement.resource_suffix and len(policy_statement.resource_suffix) > 0:
                statement_dict['Resource'] = [
                    s3bucket_arn + res_suffix
                    for res_suffix in policy_statement.resource_suffix
                ]
            else:
                statement_dict['Resource'] = [ s3bucket_arn ]

        policy_statements.append(
            Statement(**statement_dict)
        )
    return policy_statements


class S3(StackTemplate):
    def __init__(self, stack, paco_ctx, bucket_context, bucket_policy_only):
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
            stack,
            paco_ctx,
            enabled=bucket_context['config'].is_enabled(),
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
        )
        self.set_aws_name('S3', aws_name_list)
        self.bucket_context = bucket_context
        s3_ctl = self.paco_ctx.get_controller('S3')
        bucket_name = s3_ctl.get_bucket_name(bucket.paco_ref_parts)

        # Init Troposphere template
        self.init_template(bucket.title_or_name)
        template = self.template

        # Resources
        s3_resource = None
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
                                name=param_name,
                                param_type='String',
                                description='Lambda ARN parameter.',
                                value=lambda_notif.function + '.arn',
                            )
                            params[param_name] = lambda_arn_param
                        lambda_notifs.append({
                            'Event': lambda_notif.event,
                            'Function': troposphere.Ref(param_name)
                        })
                    cfn_export_dict['NotificationConfiguration']["LambdaConfigurations"] = lambda_notifs

            s3_resource = troposphere.s3.Bucket.from_dict(s3_logical_id, cfn_export_dict)
            s3_resource.DeletionPolicy = 'Retain' # We always retain. Bucket cleanup is handled by Stack hooks.
            template.add_resource(s3_resource)

            # Output
            self.create_output(
                title=s3_logical_id + 'Name',
                value=troposphere.Ref(s3_resource),
                ref=bucket.paco_ref_parts + '.name'
            )

        # Bucket Policy
        policy_statements = []
        if bucket.cloudfront_origin == True:
            # CloudFront OriginAccessIdentity resource
            cloudfront_origin_resource = troposphere.cloudfront.CloudFrontOriginAccessIdentity.from_dict(
                'CloudFrontOriginAccessIdentity',
                {'CloudFrontOriginAccessIdentityConfig': {'Comment': bucket.paco_ref_parts}},
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

            self.create_output(
                title='CloudFrontOriginAccessIdentity',
                value=troposphere.Ref(cloudfront_origin_resource),
                ref=bucket.paco_ref_parts + '.origin_id',
            )

        if len(bucket.policy) > 0:
            # Bucket Policy
            # ToDo: allow mixing CloudFront Origin policies and other bucket policies together
            bucket_arn = s3_ctl.get_bucket_arn(bucket.paco_ref_parts)
            bucket_policy_statements = create_policy_statments(
                bucket.policy,
                s3bucket_arn=bucket_arn,
            )
            for statement in bucket_policy_statements:
                policy_statements.append(statement)

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

    def delete(self):
        s3_ctl = self.paco_ctx.get_controller('S3')
        s3_ctl.empty_bucket(self.bucket_context['ref'])
        super().delete()


class S3BucketPolicy(StackTemplate):
    """
    S3 Bucket Policy

    Allows creating only selected policies for an S3 Bucket, as an s3bucket.policies model
    may have policies with dependencies on a variety of different resources and it may be
    necessary to only provision policies scoped to a specific resource.
    """

    def __init__(self, stack, paco_ctx, s3bucket, policies):
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_NAMED_IAM"])
        self.set_aws_name('BucketPolicy', self.resource_group_name, self.resource.name)

        self.init_template('S3 Bucket Policy')
        if not stack.resource.is_enabled():
            return

        s3bucket_arn_param = self.create_cfn_parameter(
            name='S3BucketArn',
            param_type='String',
            description='S3 Bucket Arn',
            value=s3bucket.paco_ref + '.arn',
        )
        s3bucket_name_param = self.create_cfn_parameter(
            name='S3BucketName',
            param_type='String',
            description='S3 Bucket Name',
            value=s3bucket.get_bucket_name(),
        )

        # Statement
        policy_statements = create_policy_statments(
            policies,
            s3bucket_arn_param=s3bucket_arn_param,
        )

        bucket_policy_resource = troposphere.s3.BucketPolicy(
            'S3BucketPolicy',
            Bucket=troposphere.Ref(s3bucket_name_param),
            PolicyDocument = Policy(
                Version = '2012-10-17',
                Statement = policy_statements,
            )
        )
        self.template.add_resource(bucket_policy_resource)

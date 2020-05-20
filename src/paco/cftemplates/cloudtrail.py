from paco.models import references
from paco.cftemplates.cftemplates import StackTemplate
from awacs.aws import Allow, Action, Principal, Statement, PolicyDocument
import awacs.logs
import troposphere
import troposphere.cloudtrail
import troposphere.cloudwatch
import troposphere.iam


class CloudTrail(StackTemplate):
    def __init__(self, stack, paco_ctx, s3_bucket_name):
        trail = stack.resource
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_IAM"])
        self.set_aws_name('CloudTrail')
        self.init_template('CloudTrail')
        template = self.template

        # create Trail resource
        trail_dict = {
            'TrailName': trail.name,
            'EnableLogFileValidation': trail.enable_log_file_validation,
            'IncludeGlobalServiceEvents': trail.include_global_service_events,
            'IsLogging': trail.is_enabled(),
            'IsMultiRegionTrail': trail.is_multi_region_trail,
            'S3BucketName': s3_bucket_name,
            'S3KeyPrefix': trail.s3_key_prefix,
        }
        if trail.enable_kms_encryption:
            cmk_arn_param = self.create_cfn_parameter(
                param_type='String',
                name='CMKArn',
                description='The KMS CMK Arn of the key used to encrypt the CloudTrail',
                value=trail.paco_ref + '.kms.arn',
            )
            trail_dict['KMSKeyId'] = troposphere.Ref(cmk_arn_param)
        if trail.cloudwatchlogs_log_group:
            log_group = trail.cloudwatchlogs_log_group
            cfn_export_dict = {
                'LogGroupName': log_group.log_group_name,
            }
            if log_group.expire_events_after_days != 'Never' and log_group.expire_events_after_days != '':
                cfn_export_dict['RetentionInDays'] = int(log_group.expire_events_after_days)
            log_group.logical_id = 'CloudTrailLogGroup'
            log_group_resource = troposphere.logs.LogGroup.from_dict(
                log_group.logical_id,
                cfn_export_dict
            )
            template.add_resource(log_group_resource)
            trail_dict['CloudWatchLogsLogGroupArn'] = troposphere.GetAtt(log_group_resource, "Arn")

            # Create a Role
            trail_role_resource = troposphere.iam.Role(
                "CloudTrailLogDeliveryRole",
                AssumeRolePolicyDocument=PolicyDocument(
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("sts", "AssumeRole")
                            ],
                            Principal=Principal("Service", "cloudtrail.amazonaws.com")
                        )
                    ]
                ),
                Policies=[
                    troposphere.iam.Policy(
                        PolicyName="CloudTrailLogGroupDelivery",
                        PolicyDocument=PolicyDocument(
                            Statement=[
                                Statement(
                                    Effect=Allow,
                                    Action=[awacs.logs.CreateLogStream],
                                    Resource=[ trail_dict['CloudWatchLogsLogGroupArn'] ]
                                ),
                                Statement(
                                    Effect=Allow,
                                    Action=[awacs.logs.PutLogEvents],
                                    Resource=[ trail_dict['CloudWatchLogsLogGroupArn'] ]
                                )
                            ]
                        )
                    )
                ]
            )
            template.add_resource(trail_role_resource)
            trail_dict['CloudWatchLogsRoleArn'] = troposphere.GetAtt(trail_role_resource, "Arn")

            # LogGroup Output
            self.create_output(
                title=log_group.logical_id + 'Arn',
                value=troposphere.GetAtt(log_group_resource, "Arn"),
                ref=log_group.paco_ref_parts + '.arn'
            )

        # CloudTrail resource
        trail.logical_id = 'CloudTrail' + self.create_cfn_logical_id(trail.name)
        trail_resource = troposphere.cloudtrail.Trail.from_dict(
            trail.logical_id,
            trail_dict
        )
        trail_resource.DependsOn = 'CloudTrailLogDeliveryRole'
        template.add_resource(trail_resource)

        # CloudTrail output
        self.create_output(
            title=trail.logical_id + 'Arn',
            value=troposphere.GetAtt(trail_resource, "Arn"),
            ref=trail.paco_ref_parts + '.arn',
        )

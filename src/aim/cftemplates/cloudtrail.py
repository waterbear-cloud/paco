import awacs.logs
import troposphere
import troposphere.cloudtrail
import troposphere.cloudwatch
import troposphere.iam
from aim.models import references
from aim.cftemplates.cftemplates import CFTemplate
from awacs.aws import Allow, Action, Principal, Statement, PolicyDocument


class CloudTrail(CFTemplate):
    def __init__(self, aim_ctx, account_ctx, aws_region, stack_group, stack_tags, trail, s3_bucket_name):
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=None,
            iam_capabilities=["CAPABILITY_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('CloudTrail')
        template = troposphere.Template()

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
        if trail.cloudwatchlogs_log_group:
            log_group = trail.cloudwatchlogs_log_group
            cfn_export_dict = {
                'LogGroupName': log_group.log_group_name,
            }
            if log_group.expire_events_after_days != 'Never' and log_group.expire_events_after_days != '':
                cfn_export_dict['RetentionInDays'] = int(log_group.expire_events_after_days)
            log_group_resource = troposphere.logs.LogGroup.from_dict(
                'CloudTrailLogGroup',
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
                                    Resource=[log_group_arn]
                                ),
                                Statement(
                                    Effect=Allow,
                                    Action=[awacs.logs.PutLogEvents],
                                    Resource=[log_group_arn]
                                )
                            ]
                        )
                    )
                ]
            )
            template.add_resource(trail_role_resource)
            trail_dict['CloudWatchLogsRoleArn'] = troposphere.GetAtt(trail_role_resource, "Arn")

        trail_resource = troposphere.cloudtrail.Trail.from_dict(
            'CloudTrail' + self.create_cfn_logical_id(trail.name),
            trail_dict
        )
        trail_resource.DependsOn = 'CloudTrailLogDeliveryRole'
        template.add_resource(trail_resource)
        self.set_template(template.to_yaml())




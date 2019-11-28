import awacs.logs
import troposphere
import troposphere.cloudtrail
import troposphere.cloudwatch
import troposphere.iam
from paco.models import references
from paco.cftemplates.cftemplates import CFTemplate
from awacs.aws import Allow, Action, Principal, Statement, PolicyDocument


class CloudTrail(CFTemplate):
    def __init__(self, paco_ctx, account_ctx, aws_region, stack_group, stack_tags, trail, s3_bucket_name):
        super().__init__(
            paco_ctx,
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
            self.register_stack_output_config(log_group.paco_ref_parts + '.arn', log_group.logical_id + 'Arn')
            log_group_output = troposphere.Output(
                log_group.logical_id + 'Arn',
                Value=troposphere.GetAtt(log_group_resource, "Arn")
            )
            template.add_output(log_group_output)

        # CloudTrail resource
        trail.logical_id = 'CloudTrail' + self.create_cfn_logical_id(trail.name)
        trail_resource = troposphere.cloudtrail.Trail.from_dict(
            trail.logical_id,
            trail_dict
        )
        trail_resource.DependsOn = 'CloudTrailLogDeliveryRole'
        template.add_resource(trail_resource)

        # CloudTrail output
        self.register_stack_output_config(trail.paco_ref_parts + '.arn', trail.logical_id + 'Arn')
        trail_output = troposphere.Output(
            trail.logical_id + 'Arn',
            Value=troposphere.GetAtt(trail_resource, "Arn"),
        )
        template.add_output(trail_output)

        self.set_template(template.to_yaml())

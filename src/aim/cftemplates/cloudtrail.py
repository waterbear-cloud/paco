from aim.models import references
from aim.cftemplates.cftemplates import CFTemplate, marshal_value_to_cfn_yaml


class CloudTrail(CFTemplate):
    def __init__(self, aim_ctx, account_ctx, aws_region, trail, s3_bucket_name):
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=None,
            aws_name="CloudTrail",
        )

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'CloudTrail'

Resources:
{0[resources_yaml]:s}

Outputs:
{0[outputs_yaml]:s}
"""
        template_table = {
            'resources_yaml': "",
            'outputs_yaml': ""
        }

        cloudtrail_fmt = """
  {0[cf_resource_name_prefix]:s}CloudTrail:
    Type: AWS::CloudTrail::Trail
    Properties:
      TrailName: {0[trailname]:s}
      EnableLogFileValidation: {0[enable_log_file_validation]:s}
      IncludeGlobalServiceEvents: {0[include_global_service_events]:s}
      IsLogging: {0[is_logging]:s}
      IsMultiRegionTrail: {0[is_multi_region_trail]:s}
      #KMSKeyId: String
      S3BucketName: {0[s3_bucket_name]:s}
      S3KeyPrefix: {0[s3_key_prefix]:s}
"""

        outputs_fmt = """
  {0[cf_resource_name_prefix]:s}CloudTrailName:
    Value: !Ref {0[cf_resource_name_prefix]:s}CloudTrail
"""

        log_group_arn = None

        cloudtrail_table = {
            'cf_resource_name_prefix': self.gen_cf_logical_name(trail.name, '_'),
            'trailname': trail.name,
            'enable_log_file_validation': marshal_value_to_cfn_yaml(trail.enable_log_file_validation),
            'include_global_service_events': marshal_value_to_cfn_yaml(trail.include_global_service_events),
            'is_logging': marshal_value_to_cfn_yaml(trail.is_enabled()),
            'is_multi_region_trail': marshal_value_to_cfn_yaml(trail.is_multi_region_trail),
            's3_bucket_name': s3_bucket_name,
            's3_key_prefix': marshal_value_to_cfn_yaml(trail.s3_key_prefix),
        }

        resources_yaml = ""
        resources_yaml += cloudtrail_fmt.format(cloudtrail_table)
        if trail.cloudwatchlogs_log_group:
            trail.cloudwatchlogs_log_group = trail.cloudwatchlogs_log_group.replace("<account>", self.account_ctx.get_name())
            trail.cloudwatchlogs_log_group = trail.cloudwatchlogs_log_group.replace("<region>", self.aws_region)
            log_group_arn = references.resolve_ref(
                trail.cloudwatchlogs_log_group,
                self.aim_ctx.project,
                account_ctx=account_ctx
            )
            cloudwatch_fmt = """
      CloudWatchLogsLogGroupArn: {0[log_group_arn]:s}
      CloudWatchLogsRoleArn: "XXX"
"""
            resources_yaml += cloudwatch_fmt.format({'log_group_arn':log_group_arn})
        outputs_yaml = ""
        outputs_yaml += outputs_fmt.format(cloudtrail_table)

        template_table['resources_yaml'] = resources_yaml
        template_table['outputs_yaml'] = outputs_yaml
        self.set_template(template_fmt.format(template_table))


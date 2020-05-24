from paco.cftemplates.cftemplates import StackTemplate
import troposphere
import troposphere.config


class Config(StackTemplate):
    def __init__(self, stack, paco_ctx, role, s3_bucket_name):
        super().__init__(stack, paco_ctx)
        self.set_aws_name('Config')
        self.init_template('Config')
        config = stack.resource

        # Parameters
        role_arn_param = self.create_cfn_parameter(
            param_type='String',
            name='AWSConfigRoleArn',
            description='IAM Role assumed by AWS Config',
            value=role.get_arn()
        )
        s3_bucket_name_param = self.create_cfn_parameter(
            param_type='String',
            name='S3BucketName',
            description='S3 Bucket',
            value=s3_bucket_name,
        )

        # ConfigurationRecorder resource
        include_global = False
        if config.global_resources_region == stack.aws_region:
            include_global = True
        config_recorder_dict = {
            'RecordingGroup': {
                'AllSupported': True,
                'IncludeGlobalResourceTypes': include_global,
            },
            'RoleARN': troposphere.Ref(role_arn_param),
        }
        config_recorder_resource = troposphere.config.ConfigurationRecorder.from_dict(
            'ConfigurationRecorder',
            config_recorder_dict
        )
        self.template.add_resource(config_recorder_resource)

        # DeliveryChannel resource
        delivery_channel_dict = {
            'ConfigSnapshotDeliveryProperties': {'DeliveryFrequency':config.delivery_frequency},
            'S3BucketName': troposphere.Ref(s3_bucket_name_param),
        }
        # ToDo: SnsTopic for Config
        #  SnsTopicARN: String

        delivery_channel_resource = troposphere.config.DeliveryChannel.from_dict(
            'DeliveryChannel',
            delivery_channel_dict,
        )
        #delivery_channel_resource.DependsOn = config_recorder_resource
        self.template.add_resource(delivery_channel_resource)

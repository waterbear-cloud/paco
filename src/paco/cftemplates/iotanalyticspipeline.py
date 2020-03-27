"""
IoT Analytics Pipeline template
"""

from paco.cftemplates.cftemplates import StackTemplate
import troposphere
import troposphere.iotanalytics


class IoTAnalyticsPipeline(StackTemplate):
    def __init__(self, stack, paco_ctx, role):
        super().__init__(stack, paco_ctx)
        self.set_aws_name('IoTAnalyticsPipeline', self.resource_group_name, self.resource_name)
        iotap = self.resource

        # Init Troposphere template
        self.init_template('IoT Analytics pipeline')
        if not iotap.is_enabled():
            return

        # Role ARN for IoT
        role_arn_param = self.create_cfn_parameter(
            param_type='String',
            name='IoTRoleArn',
            description='IoT Topic Rule Service Role ARN',
            value=role.get_arn(),
        )

        # Channel Resource
        iotchannel_logical_id = 'IoTAnalyticsChannel'
        cfn_export_dict = {}
        cfn_export_dict['ChannelName'] = iotap.name
        if iotap.channel_storage.bucket == None:
            channel_storage_dict = {'ServiceManagedS3':{}}
        else:
            channel_bucket_param = self.create_cfn_parameter(
                param_type='String',
                name='IoTAnalyticsChannelBucketName',
                description='IoT Analytics Channel storage bucket name',
                value=iotap.channel_storage.bucket + '.name',
            )
            channel_storage_dict = {
                'Bucket': troposphere.Ref(channel_bucket_param),
                'KeyPrefix':iotap.channel_storage.key_prefix,
                'RoleArn': troposphere.Ref(role_arn_param)
            }
        #cfn_export_dict['ChannelStorage'] = channel_storage_dict
        cfn_export_dict['RetentionPeriod'] = convert_expire_to_cfn_dict(iotap.channel_storage.expire_events_after_days)
        iotap_channel_resource = troposphere.iotanalytics.Channel.from_dict(
            iotchannel_logical_id,
            cfn_export_dict
        )
        self.template.add_resource(iotap_channel_resource)

        # Pipeline Resource

        # Dataset Resource

def convert_expire_to_cfn_dict(expire):
    if expire == 0:
        return {'Unlimited': True}
    else:
        return {'NumberOfDays': expire}
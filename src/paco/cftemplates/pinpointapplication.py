from paco.cftemplates.cftemplates import StackTemplate
import troposphere
import troposphere.pinpoint


class PinpointApplication(StackTemplate):
    def __init__(self, stack, paco_ctx):
        pinpoint_app = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name('PinpointApp', self.resource_group_name, self.resource.name)

        self.init_template('Pinpoint Application')
        if not pinpoint_app.is_enabled(): return

        # Pinpoint Application
        pinpoint_app_logical_id = 'PinpointApplication'
        pinpointapp_resource = troposphere.pinpoint.App(
            pinpoint_app_logical_id,
            Name=pinpoint_app.title,
        )
        self.template.add_resource(pinpointapp_resource)

        if pinpoint_app.sms_channel:
            cfn_export_dict = pinpoint_app.sms_channel.cfn_export_dict
            cfn_export_dict['ApplicationId'] = troposphere.Ref(pinpoint_app_logical_id)
            sms_channel_resource = troposphere.pinpoint.SMSChannel.from_dict(
                'SMSChannel',
                cfn_export_dict,
            )
            self.template.add_resource(sms_channel_resource)

        if pinpoint_app.email_channel:
            cfn_export_dict = pinpoint_app.email_channel.cfn_export_dict
            cfn_export_dict['ApplicationId'] = troposphere.Ref(pinpoint_app_logical_id)
            cfn_export_dict['Identity'] = f'arn:aws:ses:{self.aws_region}:{self.account_ctx.id}:identity/{pinpoint_app.email_channel.from_address}'
            email_channel_resource = troposphere.pinpoint.EmailChannel.from_dict(
                'EmailChannel',
                cfn_export_dict,
            )
            self.template.add_resource(email_channel_resource)

        # Output
        self.create_output(
            title=pinpointapp_resource.title + 'Id',
            description="Pinpoint Application Id",
            value=troposphere.Ref(pinpointapp_resource),
            ref=pinpoint_app.paco_ref_parts + ".id"
        )
        self.create_output(
            title=pinpointapp_resource.title + 'Arn',
            description="Pinpoint Application Arn",
            value=troposphere.GetAtt(pinpointapp_resource, "Arn"),
            ref=pinpoint_app.paco_ref_parts + ".arn"
        )

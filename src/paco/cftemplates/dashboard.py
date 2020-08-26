from paco.cftemplates.cftemplates import StackTemplate
from paco.core.exception import UnsupportedCloudFormationParameterType
import troposphere
import troposphere.cloudwatch


class CloudWatchDashboard(StackTemplate):
    def __init__(self, stack, paco_ctx):
        dashboard = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name('Dashboard', self.resource_group_name, self.resource.name)
        self.init_template('CloudWatch Dashboard')

        if not dashboard.is_enabled(): return

        # Parameters for variables
        if dashboard.variables:
            for key, value in dashboard.variables.items():
                if type(value) == type(str()):
                    param_type = 'String'
                elif type(value) == type(int()) or type(value) == type(float()):
                    param_type = 'Number'
                else:
                    raise UnsupportedCloudFormationParameterType(
                        "Can not cast {} of type {} to a CloudFormation Parameter type.".format(
                            value, type(value)
                        )
                    )
                variable_param = self.create_cfn_parameter(
                    param_type=param_type,
                    name=key,
                    description='Dashboard {} Variable'.format(key),
                    value=value
                )

        # Region Parameter
        region_param = self.create_cfn_parameter(
            param_type='String',
            name='AwsRegion',
            description='Dashboard Region Variable',
            value=self.aws_region
        )

        # Dashboard resource
        dashboard_logical_id = 'Dashboard'
        body = troposphere.Sub(dashboard.dashboard_file)
        cfn_export_dict = {
            'DashboardBody': body,
            'DashboardName': dashboard.title_or_name
        }
        dashboard_resource = troposphere.cloudwatch.Dashboard.from_dict(
            dashboard_logical_id,
            cfn_export_dict
        )
        self.template.add_resource(dashboard_resource)

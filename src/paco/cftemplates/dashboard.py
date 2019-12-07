import troposphere
import troposphere.cloudwatch
from paco.cftemplates.cftemplates import CFTemplate
from paco.models import references


class CloudWatchDashboard(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        app_id,
        grp_id,
        res_id,
        dashboard,
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=dashboard.is_enabled(),
            config_ref=dashboard.paco_ref_parts,
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('Dashboard', grp_id, res_id)
        self.init_template('CloudWatch Dashboard')

        if not dashboard.is_enabled():
            self.set_template(self.template.to_yaml())
            return

        # Parameters for variables
        if dashboard.variables and dashboard.is_enabled():
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
                    value=value,
                    use_troposphere=True
                )
                self.template.add_parameter(variable_param)

        # Region Parameter
        region_param = self.create_cfn_parameter(
            param_type='String',
            name='AwsRegion',
            description='Dashboard Region Variable',
            value=aws_region,
            use_troposphere=True
        )
        self.template.add_parameter(region_param)

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

        # Generate the Template
        self.set_template(self.template.to_yaml())

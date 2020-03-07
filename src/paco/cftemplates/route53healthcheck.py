"""
CloudFormation template for a Route53 health check
"""
import troposphere
import troposphere.route53
import troposphere.cloudwatch
from paco.cftemplates.cw_alarms import CFBaseAlarm
from paco.models import references
from paco.models.locations import get_parent_by_interface
from paco.models.metrics import CloudWatchAlarm


class Route53HealthCheck(CFBaseAlarm):
    """
    CloudFormation template for a Route53 health check
    """
    def __init__(self, stack, paco_ctx, health_check, app_aws_region):
        # Route53 metrics only go to us-east-1
        # The app_aws_region is the region of the Application for the Name and Tags
        self.app_aws_region = app_aws_region
        self.health_check = health_check
        self.alarm_action_param_map = {}
        self.notification_param_map = {}
        super().__init__(stack, paco_ctx)
        self.set_aws_name('Route53HealthCheck', self.health_check.name)

        # Troposphere Template Initialization
        self.init_template('Route 53 health check')

        if not self.health_check.is_enabled(): return

        # Health check Resource
        health_check_logical_id = self.create_cfn_logical_id('Route53HealthCheck' + self.health_check.name)
        cfn_export_dict = {}
        cfn_export_dict['HealthCheckConfig'] = self.health_check.cfn_export_dict
        if self.health_check.ip_address != None:
            # Set the IPAddress to ping
            ip_address_param = self.create_cfn_parameter(
                param_type='String',
                name='IPAddress',
                description='IP address to monitor.',
                value=self.health_check.ip_address + '.address',
            )
            cfn_export_dict['HealthCheckConfig']['IPAddress'] = troposphere.Ref(ip_address_param)
        else:
            # FullyQualifiedDomainName can be either a domain_name or a ref to an ALB endpoint
            if self.health_check.domain_name != None:
                fqdn_value = self.health_check.domain_name
            else:
                fqdn_value = self.health_check.load_balancer + '.dnsname'
            fqdn_param = self.create_cfn_parameter(
                param_type = 'String',
                name = 'FQDNEndpoint',
                description = 'Fully-qualified domain name of the endpoint to monitor.',
                value = fqdn_value,
            )
            cfn_export_dict['HealthCheckConfig']['FullyQualifiedDomainName'] = troposphere.Ref(fqdn_param)
        # Set the Name in the HealthCheckTags
        # Route53 is global, but we add the app's region in the name
        cfn_export_dict['HealthCheckTags'] = troposphere.Tags(Name=self.aws_name + '-' + self.app_aws_region)

        health_check_resource = troposphere.route53.HealthCheck.from_dict(
            health_check_logical_id,
            cfn_export_dict
        )
        self.template.add_resource(health_check_resource)

        # CloudWatch Alarm
        # ToDo: allow configurtion of this alarm from the model
        alarm = CloudWatchAlarm('HealthCheckAlarm', self.health_check)
        alarm.overrode_region_name = 'us-east-1'
        alarm.metric_name = "HealthCheckPercentageHealthy"
        alarm.classification = 'health'
        alarm.severity = 'critical'
        alarm.namespace = "AWS/Route53"
        alarm.period = 60
        alarm.evaluation_periods = 1
        alarm.threshold = 18.0 # As recommended by AWS
        alarm.comparison_operator = 'LessThanOrEqualToThreshold'
        alarm.statistic = "Average"
        alarm.treat_missing_data = 'breaching'
        cfn_export_dict = alarm.cfn_export_dict
        cfn_export_dict['Dimensions'] = [{
            'Name': 'HealthCheckId',
            'Value': troposphere.Ref(health_check_resource),
        }]
        cfn_export_dict['Namespace'] = "AWS/Route53"
        notification_cfn_refs = self.create_notification_params(alarm)
        cfn_export_dict['AlarmDescription'] = alarm.get_alarm_description(notification_cfn_refs)
        self.set_alarm_actions_to_cfn_export(alarm, cfn_export_dict)
        alarm_resource = troposphere.cloudwatch.Alarm.from_dict(
            'HealthCheckAlarm',
            cfn_export_dict
        )
        alarm_resource.DependsOn = health_check_logical_id
        self.template.add_resource(alarm_resource)

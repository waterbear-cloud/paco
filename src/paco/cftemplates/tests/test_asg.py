from paco.cftemplates.tests import BaseTestProject
from paco.cftemplates.asg import ASG
import troposphere
import troposphere.autoscaling


class TestASG(BaseTestProject):

    fixture_name = 'config_city'
    app_name = 'app'
    netenv_name = 'res'
    group_name = 'things'

    def test_asg(self):
        netenv_ctl = self.paco_ctx.get_controller('netenv', None, self.env_region)
        asg_resource = self.get_resource_by_type('ASG')
        troposphere_tmpl = asg_resource.stack.template.template

        # ASG has an AutoScalingGroup Resource
        assert troposphere_tmpl.resources['ASG'].resource_type, troposphere.autoscaling.AutoScalingGroup.resource_type

        # Output
        self.assertIsInstance(troposphere_tmpl.outputs['ASGName'], troposphere.Output)

        # LaunchConfiguration
        # BlockDeviceMappings: one mapping
        assert troposphere_tmpl.resources['LaunchConfiguration'].properties['BlockDeviceMappings'][0]['DeviceName'], '/dev/sda1'
        assert len(troposphere_tmpl.resources['LaunchConfiguration'].properties['BlockDeviceMappings']), 1

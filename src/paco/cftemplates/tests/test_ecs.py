from paco.cftemplates.tests import BaseTestProject
import troposphere
import troposphere.ecs


class TestECS(BaseTestProject):

    fixture_name = 'config_city'
    app_name = 'app'
    netenv_name = 'res'
    group_name = 'things'

    def test_ecs(self):
        netenv_ctl = self.paco_ctx.get_controller('netenv', None, self.env_region)
        ecs_resource = self.get_resource_by_type('ECSCluster')
        troposphere_tmpl = ecs_resource.stack.template.template

        # ECS Cluster has a Cluster resource
        assert troposphere_tmpl.resources['Cluster'].resource_type, troposphere.ecs.Cluster.resource_type

        # Cluster Name Output
        self.assertIsInstance(troposphere_tmpl.outputs['ClusterName'], troposphere.Output)

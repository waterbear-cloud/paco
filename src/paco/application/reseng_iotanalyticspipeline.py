from paco import cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
from paco.models.iam import Role
from paco.models.references import get_model_obj_from_ref
import paco.cftemplates.iotanalyticspipeline


class IoTAnalyticsPipelineResourceEngine(ResourceEngine):

    def init_resource(self):
        # Create a Role for the IoT Topic Rule to assume
        role_name = "iot_analytics"

        # add needed Statements to the Policy
        statements = []

        if self.resource.channel_storage.bucket != None:
            bucket = get_model_obj_from_ref(self.resource.channel_storage.bucket, self.paco_ctx.project)
            statements.append({
                'effect': 'Allow',
                'action': ['s3:*'],
                'resource': [
                    f"arn:aws:s3:::" + bucket.get_aws_name(),
                    f"arn:aws:s3:::" + bucket.get_aws_name() + "/*"
                ],
            })

        role_dict = {
            'enabled': self.resource.is_enabled(),
            'path': '/',
            'role_name': "IoTAnalytics",
            'assume_role_policy': {'effect': 'Allow', 'service': ['iotanalytics.amazonaws.com']},
        }
        if len(statements) > 0:
            role_dict['policies'] = [{'name': 'IoTTopicRule', 'statement': statements}]

        role = Role(role_name, self.resource)
        role.apply_config(role_dict)
        iam_role_id = self.gen_iam_role_id(self.resource.name, role_name)
        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_role(
            region=self.aws_region,
            resource=self.resource,
            role=role,
            iam_role_id=iam_role_id,
            stack_group=self.stack_group,
            stack_tags=self.stack_tags
        )

        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.iotanalyticspipeline.IoTAnalyticsPipeline,
            stack_tags=self.stack_tags,
            extra_context={'role': role},
        )


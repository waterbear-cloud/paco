from paco import cftemplates
from paco.application.res_engine import ResourceEngine
from paco.models.references import get_model_obj_from_ref
from paco.core.yaml import YAML
from paco.models.iam import Role
import paco.cftemplates.iottopicrule


class IoTTopicRuleResourceEngine(ResourceEngine):

    def init_resource(self):

        # Create a Role for the IoT Topic Rule to assume
        role_name = "iot_topic_rule"

        # add needed Statements to the Policy
        statements = []
        for action in self.resource.actions:
            if action.iotanalytics != None:
                iotap = get_model_obj_from_ref(action.iotanalytics.pipeline, self.paco_ctx.project)
                iotap_name_sub = "paco.sub '${" + iotap.paco_ref + ".channel.name}'"
                statements.append({
                    'effect': 'Allow',
                    'action': ['iotanalytics:BatchPutMessage'],
                    'resource': f"arn:aws:iotanalytics:{self.aws_region}:{self.account_ctx.id}:channel/{iotap_name_sub}",
                })

        role_dict = {
            'enabled': self.resource.is_enabled(),
            'path': '/',
            'role_name': "IoTTopicRule",
            'assume_role_policy': {'effect': 'Allow', 'service': ['iot.amazonaws.com']},
            'policies': [{'name': 'IoTTopicRule', 'statement': statements}],
        }
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
            paco.cftemplates.iottopicrule.IoTTopicRule,
            stack_tags=self.stack_tags,
            extra_context={
                'role': role,
            }
        )

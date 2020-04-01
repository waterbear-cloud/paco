from paco import cftemplates
from paco.application.res_engine import ResourceEngine
from paco.models.references import get_model_obj_from_ref
from paco.core.yaml import YAML
from paco.models.iam import Role
from paco import utils
import paco.cftemplates.iottopicrule


class IoTTopicRuleResourceEngine(ResourceEngine):

    def init_resource(self):

        # Create a Role for the IoT Topic Rule to assume
        role_name = "iot_topic_rule"

        # add needed Statements to the Policy
        statements = []
        role_params = []
        for action in self.resource.actions:
            if action.iotanalytics != None:
                iotap = get_model_obj_from_ref(action.iotanalytics.pipeline, self.paco_ctx.project)
                iotap_hash = utils.md5sum(str_data='.'.join(iotap.paco_ref_parts))
                channel_key = f'ChannelName{iotap_hash}'
                role_params.append({
                    'description': f'IoT Analytics channel for {iotap.name}',
                    'type': 'String',
                    'key': channel_key,
                    'value': iotap.paco_ref + ".channel.name"
                })
                iotap_name_sub = "paco.sub '${" + iotap.paco_ref + ".channel.name}'"
                resource_cfn = "!Join [ '', [ {}, {} ] ]".format(
                    f"'arn:aws:iotanalytics:{self.aws_region}:{self.account_ctx.id}:channel/'",
                    f"!Ref {channel_key}",
                )
                statements.append({
                    'effect': 'Allow',
                    'action': ['iotanalytics:BatchPutMessage'],
                    'resource': resource_cfn,
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
            stack_tags=self.stack_tags,
            template_params=role_params,
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

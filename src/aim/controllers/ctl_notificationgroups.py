import aim.cftemplates
import os
import pathlib
from aim import utils
from aim.controllers.controllers import Controller
from aim.stack_group import StackGroup, Stack, StackTags
from aim.core.yaml import YAML
from aim.core.exception import StackException


yaml=YAML()
yaml.default_flow_sytle = False

class NotificationGroupsStackGroup(StackGroup):
    def __init__(
        self,
        aim_ctx,
        account_ctx,
        region,
        group_name,
        controller,
        resource_ref,
        config,
        stack_tags
    ):
        aws_name = group_name
        super().__init__(
            aim_ctx,
            account_ctx,
            group_name,
            aws_name,
            controller
        )
        self.region = region
        self.resource_ref = resource_ref
        self.config = config
        self.stack_tags = stack_tags

    def init(self):
        "init"
        # create a template
        sns_topics_config = [topic for topic in self.config.values()]
        aim.cftemplates.SNSTopics(
            self.aim_ctx,
            self.account_ctx,
            self.region,
            self,
            StackTags(self.stack_tags),
            'NG',
            None,
            sns_topics_config,
            self.resource_ref
        )

class NotificationGroupsController(Controller):
    def __init__(self, aim_ctx):
        super().__init__(
            aim_ctx,
            "NG",
            None
        )
        try:
            self.groups = self.aim_ctx.project['resource']['notificationgroups']
        except KeyError:
            self.init_done = True
            return
        self.init_done = False

    def init(self, init_config):
        "Initialize controller"
        if self.init_done:
            return
        # inject the controller into the model
        self.groups.resolve_ref_obj = self
        stack_tags = StackTags()
        self.account_ctx = self.aim_ctx.get_account_context(account_ref=self.groups.account)

        if self.groups.regions == ['ALL']:
            self.active_regions = self.aim_ctx.project.active_regions
        else:
            self.active_regions = self.groups.regions

        # create a NotificationGroup stack group for each active region
        self.ng_stackgroups = {}
        for region in self.active_regions:
            config_ref = self.groups[region].aim_ref_parts
            stackgroup = NotificationGroupsStackGroup(
                self.aim_ctx,
                self.account_ctx,
                region,
                'SNS',
                self,
                config_ref,
                self.groups[region],
                StackTags(stack_tags)
            )
            self.ng_stackgroups[region] = stackgroup
            stackgroup.init()
        self.init_done = True

    def validate(self):
        "Validate"
        for stackgroup in self.ng_stackgroups.values():
            stackgroup.validate()

    def provision(self):
        "Provision"
        for stackgroup in self.ng_stackgroups.values():
            stackgroup.provision()

        # Save to Outputs/MonitorConfig/NotificationGroups.yaml file
        regional_output = { 'notificationgroups': {} }
        for stackgroup in self.ng_stackgroups.values():
            regional_output['notificationgroups'][stackgroup.region] = stackgroup.stacks[0].output_config_dict['notificationgroups']
        resources_config_path = os.path.join(
            self.aim_ctx.project_folder,
            'Outputs',
            'Resources'
        )
        pathlib.Path(resources_config_path).mkdir(parents=True, exist_ok=True)
        resources_config_yaml_path = os.path.join(resources_config_path, 'NotificationGroups.yaml')
        with open(resources_config_yaml_path, "w") as output_fd:
            yaml.dump(data=regional_output, stream=output_fd)

    def delete(self):
        "Delete"
        for stackgroup in self.ng_stackgroups.values():
            stackgroup.delete()

    def resolve_ref(self, ref):
        # ToDo: only resolves .arn refs
        if ref.last_part == 'arn':
            stackgroup = self.ng_stackgroups[ref.parts[2]]
            stack = stackgroup.get_stack_from_ref(ref)
            return stack
        else:
            return None

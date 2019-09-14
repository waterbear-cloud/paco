import aim.cftemplates
import os
import pathlib
from aim.controllers.controllers import Controller
from aim.stack_group import StackGroup, Stack, StackTags
from aim.core.yaml import YAML

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
        sns_topics_config = [topic for topic in self.aim_ctx.project['notificationgroups'].values()]
        aim.cftemplates.SNSTopics(
            self.aim_ctx,
            self.account_ctx,
            self.region,
            self,
            StackTags(self.stack_tags),
            'NG',
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
        self.groups = self.aim_ctx.project['notificationgroups']
        self.aim_ctx.log("NotificationGroups: Configuration")
        self.init_done = False
        self.active_regions = self.aim_ctx.project.active_regions

    def init(self, init_config):
        if self.init_done:
            return
        self.init_done = True
        stack_tags = StackTags()
        self.config = self.aim_ctx.project['notificationgroups']
        self.account_ctx = self.aim_ctx.get_account_context(account_ref=self.config.account)
        self.config_ref = 'notificationgroups'

        # create a NotificationGroup stack group for each active region
        self.ng_stackgroups = []
        for region in self.active_regions:
            stackgroup = NotificationGroupsStackGroup(
                self.aim_ctx,
                self.account_ctx,
                region,
                'SNS',
                self,
                self.config_ref,
                self.config,
                StackTags(stack_tags)
            )
            self.ng_stackgroups.append(stackgroup)
            stackgroup.init()

    def validate(self):
        "Validate"
        for stackgroup in self.ng_stackgroups:
            sstackgroup.validate()

    def provision(self):
        "Provision"
        for stackgroup in self.ng_stackgroups:
            stackgroup.provision()

        # Save to Outputs/MonitorConfig/NotificationGroups.yaml file
        regional_output = { 'notificationgroups': {} }
        for stackgroup in self.ng_stackgroups:
            regional_output['notificationgroups'][stackgroup.region] = stackgroup.stacks[0].output_config_dict['notificationgroups']
        monitor_config_path = os.path.join(
            self.aim_ctx.project_folder,
            'Outputs',
            'MonitorConfig'
        )
        pathlib.Path(monitor_config_path).mkdir(parents=True, exist_ok=True)
        monitor_config_yaml_path = os.path.join(monitor_config_path, 'NotificationGroups.yaml')
        with open(monitor_config_yaml_path, "w") as output_fd:
            yaml.dump(data=regional_output, stream=output_fd)

    def delete(self):
        "Delete"
        for stackgroup in self.ng_stackgroups():
            stackgroup.delete()

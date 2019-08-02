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
        sns_topics_config = []
        # TODO: Build a list of ISNSTopic configurations
        breakpoint()
        ng_sns_template = aim.cftemplates.SNSTopics(
            self.aim_ctx,
            self.account_ctx,
            self.region,
            'NG',
            sns_topics_config,
            self.resource_ref
        )

        ng_sns_stack = Stack(
            self.aim_ctx,
            self.account_ctx,
            self,
            None, # deprecated
            ng_sns_template,
            aws_region=self.region,
            stack_tags=StackTags(self.stack_tags)
        )
        self.add_stack_order(ng_sns_stack)

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

    def init(self, init_config):
        if self.init_done:
            return
        self.init_done = True
        stack_tags = StackTags()
        self.config = self.aim_ctx.project['notificationgroups']
        self.account_ctx = self.aim_ctx.get_account_context(account_ref=self.config.account)

        # create a stack group
        self.ng_stackgroup = NotificationGroupsStackGroup(
            self.aim_ctx,
            self.account_ctx,
            self.config.region,
            'SNS',
            self,
            'monitor.ref notificationgroups',
            self.config,
            StackTags(stack_tags)
        )
        self.ng_stackgroup.init()

    def validate(self):
        "Validate"
        self.ng_stackgroup.validate()

    def provision(self):
        "Provision"
        self.ng_stackgroup.provision()

        # Save to Outputs/MonitorConfig/NotificationGroups.yaml file
        data = self.ng_stackgroup.stacks[0].output_config_dict
        monitor_config_path = os.path.join(
            self.aim_ctx.project_folder,
            'Outputs',
            'MonitorConfig'
        )
        pathlib.Path(monitor_config_path).mkdir(parents=True, exist_ok=True)
        monitor_config_yaml_path = os.path.join(monitor_config_path, 'NotificationGroups.yaml')
        with open(monitor_config_yaml_path, "w") as output_fd:
            yaml.dump(data=data, stream=output_fd)

    def delete(self):
        "Delete"
        self.ng_stackgroup.delete()

import aim.cftemplates
import os
import pathlib
from aim.controllers.controllers import Controller
from aim.stack_group import StackGroup, Stack, StackTags
from aim.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class LogGroupsStackGroup(StackGroup):
    def __init__(
        self,
        aim_ctx,
        account_ctx,
        region,
        group_name,
        controller,
        resource_ref,
        resource,
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
        self.resource = resource
        self.stack_tags = stack_tags

    def init(self):
        "init"
        # create a template
        lg_template = aim.cftemplates.LogGroups(
            self.aim_ctx,
            self.account_ctx,
            self.region,
            'LG',
            self.resource,
            self.resource_ref
        )
        lg_stack = Stack(
            self.aim_ctx,
            self.account_ctx,
            self,
            None, # deprecated
            lg_template,
            aws_region=self.region,
            stack_tags=StackTags(self.stack_tags)
        )
        self.add_stack_order(lg_stack)

class LogGroupsController(Controller):
    def __init__(self, aim_ctx):
        super().__init__(
            aim_ctx,
            "LG",
            None
        )
        self.aim_ctx.log("LogGroups: Configuration")
        self.init_done = False

    def init_log_sources(self, resource, account_ctx):
        stack_tags = StackTags()
        self.resource = resource
        self.account_ctx = account_ctx
        self.lg_stackgroup = LogGroupsStackGroup(
            self.aim_ctx,
            self.account_ctx,
            self.resource.region_name,
            'LG',
            self,
            'loggroups ref',
            self.resource,
            StackTags(stack_tags)
        )
        self.lg_stackgroup.init()

    def validate(self):
        "Validate"
        self.lg_stackgroup.validate()

    def provision(self):
        "Provision"
        self.lg_stackgroup.provision()

    def delete(self):
        "Delete"
        self.lg_stackgroup.delete()

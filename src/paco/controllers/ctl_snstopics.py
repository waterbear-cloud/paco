import paco.cftemplates
import os
import pathlib
from paco import utils
from paco.controllers.controllers import Controller
from paco.stack import StackGroup, Stack, StackTags
from paco.core.yaml import YAML
from paco.core.exception import StackException


yaml=YAML()
yaml.default_flow_sytle = False

class SNSTopicsStackGroup(StackGroup):
    def __init__(
        self,
        paco_ctx,
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
            paco_ctx,
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
        self.paco_ctx.log_start('Init', self.config)
        sns_topics_config = [topic for topic in self.config.values()]
        stack = self.add_new_stack(
            self.region,
            self.config,
            paco.cftemplates.SNSTopics,
            stack_tags=StackTags(self.stack_tags),
            extra_context={'grp_id': 'NG'}
        )
        self.paco_ctx.log_finish('Init', self.config)

class SNTopicsGroupsController(Controller):
    def __init__(self, paco_ctx):
        super().__init__(
            paco_ctx,
            "NG",
            None
        )
        try:
            self.groups = self.paco_ctx.project['resource']['snstopics']
        except KeyError:
            self.init_done = True
            return
        self.init_done = False

    def init(self, command=None, model_obj=None):
        "Initialize controller"
        if self.init_done:
            return
        # inject the controller into the model
        self.groups.resolve_ref_obj = self
        stack_tags = StackTags()
        # there is no snstopics.yaml for this project
        if self.groups.account == None:
            self.init_done = True
            return
        self.account_ctx = self.paco_ctx.get_account_context(account_ref=self.groups.account)

        if self.groups.regions == ['ALL']:
            self.active_regions = self.paco_ctx.project.active_regions
        else:
            self.active_regions = self.groups.regions

        # create a SNSTopicsGroup stack group for each active region
        self.ng_stackgroups = {}
        for region in self.active_regions:
            config_ref = self.groups[region].paco_ref_parts
            stackgroup = SNSTopicsStackGroup(
                self.paco_ctx,
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

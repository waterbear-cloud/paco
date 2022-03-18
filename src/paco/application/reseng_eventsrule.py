from paco import cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
import paco.cftemplates.eventsrule
from paco.stack import StackHooks

yaml=YAML()
yaml.default_flow_sytle = False

class EventsRuleResourceEngine(ResourceEngine):

    def init_resource(self):

        stack_hooks = StackHooks()
        # Stack hooks for saving state to the Paco bucket
        stack_hooks.add(
            name='EventsRule.State',
            stack_action=['create', 'update'],
            stack_timing='post',
            hook_method=self.stack_hook_codebuild_state,
            cache_method=self.stack_hook_codebuild_state_cache_id
        )

        # CloudWatch Events Rule
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.eventsrule.EventsRule,
            stack_tags=self.stack_tags,
            stack_hooks=stack_hooks
        )

    def stack_hook_codebuild_state_cache_id(self, hook, config):
        return "placeholder"

    def stack_hook_codebuild_state(self, hook, config):
        return
from paco import cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
import paco.cftemplates.eventsrule
from paco.models.locations import get_parent_by_interface
from paco.stack import StackHooks
from paco import utils

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
            account_ctx=self.account_ctx,
            stack_tags=self.stack_tags,
            #stack_hooks=stack_hooks
        )

    def stack_hook_codebuild_state_cache_id(self, hook, config):
        return "placeholder"

    def stack_hook_codebuild_state(self, hook, config):
        if self.app_engine.ref_type == 'service':
            netenv_id = self.service_name
            env_id = self.service_account
        else:
            netenv_id = self.app_engine.env_ctx.netenv.name
            env_id = self.app_engine.env_ctx.netenv.name

        monitoring = self.resource.monitoring
        if monitoring != None and monitoring.is_enabled() == True:
            notifications = None
            if monitoring.notifications != None and len(monitoring.notifications.keys()) > 0:
                notifications = monitoring.notifications
            else:
                app_config = get_parent_by_interface(self.resource, schemas.IApplication)
                notifications = app_config.notifications

            if notifications != None and len(notifications.keys()) > 0:
                # Store the Notification state for this EventRule
                state_key = f'{netenv_id}-{env_id}-{app_id}-{grp_id}-{self.resource.name}'
                state_config = {
                    'nontifications': utils.obj_to_dict(notifications)
                }
                self.paco_ctx.store_resource_state(
                    self.resource.type,
                    state_key,
                    self.account_ctx.id,
                    self.aws_region,
                    state_config)

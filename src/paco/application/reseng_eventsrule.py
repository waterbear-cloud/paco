import json
import paco.cftemplates.eventsrule

from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
from paco.models import schemas
from paco.models.locations import get_parent_by_interface
from paco.models.references import get_model_obj_from_ref
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
            hook_method=self.stack_hook_eventsrule_state,
            cache_method=self.stack_hook_eventsrule_state_cache_id,
        )

        # CloudWatch Events Rule
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.eventsrule.EventsRule,
            account_ctx=self.account_ctx,
            stack_tags=self.stack_tags,
            stack_hooks=stack_hooks
        )

    def gen_state_config(self, source):
        monitoring = self.resource.monitoring
        if monitoring != None and monitoring.is_enabled() == True:
            notifications = None
            if monitoring.notifications != None and len(monitoring.notifications.keys()) > 0:
                notifications = monitoring.notifications
            else:
                app_config = get_parent_by_interface(self.resource, schemas.IApplication)
                notifications = app_config.notifications

        source_obj = get_model_obj_from_ref(source, self.paco_ctx.project)
        state_config = {
            'type': source_obj.type,
            'notifications': []
        }
        if notifications == None or len(notifications.keys()) <= 0:
            return state_config
            # Store the Notification state for this EventRule
        if self.resource.event_pattern == None:
            return state_config

        if source_obj.type == 'CodeBuild.Build':
            state_config['project_name'] = source_obj._stack.template.get_project_name()

            state_config['notifications'] =  {}
            for group_id in notifications.keys():
                notify_group = notifications[group_id]
                state_config['notifications'][group_id] = {}
                state_config['notifications'][group_id]['severity'] = notify_group.severity
                state_config['notifications'][group_id]['groups'] = []
                state_config['notifications'][group_id]['groups'].extend(notify_group.groups)
                state_config['notifications'][group_id]['slack_channels'] = []
                state_config['notifications'][group_id]['slack_channels'].extend(notify_group.slack_channels)

        return state_config

    def stack_hook_eventsrule_state_cache_id(self, hook, config):
        state_list = []
        for source in self.resource.event_pattern.source:
            state_config = self.gen_state_config(source)
            state_list.append(state_config)

        return utils.md5sum(str_data=json.dumps(state_list))

    def stack_hook_eventsrule_state(self, hook, config):
        for source in self.resource.event_pattern.source:
            state_config = self.gen_state_config(source)
            if state_config != None:
                state_key = state_config['project_name']
                self.paco_ctx.store_resource_state(
                    self.resource.type,
                    state_key,
                    self.account_ctx.id,
                    self.aws_region,
                    state_config)

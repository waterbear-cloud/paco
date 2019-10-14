from aim import models, cftemplates
from aim.application.res_engine import ResourceEngine
from aim.core.yaml import YAML
import aim.cftemplates.eventsrule

yaml=YAML()
yaml.default_flow_sytle = False

class EventsRuleResourceEngine(ResourceEngine):

    def init_resource(self):
        # CloudWatch Events Rule
        aim.cftemplates.eventsrule.EventsRule(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.env_ctx,
            self.app_id,
            self.grp_id,
            self.res_id,
            self.resource,
            self.resource.aim_ref_parts
        )

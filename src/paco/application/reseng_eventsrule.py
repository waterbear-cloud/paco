from paco import cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
import paco.cftemplates.eventsrule

yaml=YAML()
yaml.default_flow_sytle = False

class EventsRuleResourceEngine(ResourceEngine):

    def init_resource(self):
        # CloudWatch Events Rule
        paco.cftemplates.eventsrule.EventsRule(
            self.paco_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.env_ctx,
            self.app_id,
            self.grp_id,
            self.res_id,
            self.resource,
            self.resource.paco_ref_parts
        )

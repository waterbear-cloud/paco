from paco import cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
import paco.cftemplates.eventsrule

yaml=YAML()
yaml.default_flow_sytle = False

class EventsRuleResourceEngine(ResourceEngine):

    def init_resource(self):
        # CloudWatch Events Rule
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.eventsrule.EventsRule,
            stack_tags=self.stack_tags,
        )

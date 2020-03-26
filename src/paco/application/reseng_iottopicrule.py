from paco import cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
import paco.cftemplates.iottopicrule


class IoTTopicRuleResourceEngine(ResourceEngine):

    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.iottopicrule.IoTTopicRule,
            stack_tags=self.stack_tags,
        )

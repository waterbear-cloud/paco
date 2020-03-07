import paco.cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class SNSTopicResourceEngine(ResourceEngine):

    def init_resource(self):
        stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.SNSTopics,
            stack_tags=self.stack_tags
        )

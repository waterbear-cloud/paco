import paco.cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class SNSTopicResourceEngine(ResourceEngine):

    def init_resource(self):
        sns_topics_config = [self.resource]
        # Strip the last part as SNSTopics loops thorugh a list and will
        # append the name to ref when it needs.
        res_config_ref = '.'.join(self.resource.paco_ref_parts.split('.')[:-1])
        paco.cftemplates.SNSTopics(
            self.paco_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.grp_id,
            self.res_id,
            sns_topics_config,
            res_config_ref
        )
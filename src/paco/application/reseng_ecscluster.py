from paco import cftemplates
from paco.application.res_engine import ResourceEngine


class ECSClusterResourceEngine(ResourceEngine):
    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.ECSCluster,
            stack_tags=self.stack_tags,
        )

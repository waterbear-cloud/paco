from paco import cftemplates
from paco.application.res_engine import ResourceEngine


class ElastiCacheRedisResourceEngine(ResourceEngine):

    def init_resource(self):
        # ElastiCache Redis CloudFormation
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.ElastiCache,
            stack_tags=self.stack_tags,
        )

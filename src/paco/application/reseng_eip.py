from paco import cftemplates
from paco.application.res_engine import ResourceEngine

class EIPResourceEngine(ResourceEngine):

    def init_resource(self):
        # EIP
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.EIP,
            stack_tags=self.stack_tags,
        )

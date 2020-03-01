from paco import cftemplates
from paco.application.res_engine import ResourceEngine


class EFSResourceEngine(ResourceEngine):
    def init_resource(self):
        network = self.env.network
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.EFS,
            stack_tags=self.stack_tags,
            extra_context={'network': network},
        )

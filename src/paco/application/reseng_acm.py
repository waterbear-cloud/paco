from paco.application.res_engine import ResourceEngine
from paco.stack.botostacks.acm import ACMBotoStack


class ACMResourceEngine(ResourceEngine):

    def init_resource(self):
        self.stack_group.add_new_boto_stack(
            self.aws_region,
            self.resource,
            ACMBotoStack,
        )

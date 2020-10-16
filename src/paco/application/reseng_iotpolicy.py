from paco.application.res_engine import ResourceEngine
from paco.stack.botostacks.iotpolicy import IoTPolicyBotoStack

class IoTPolicyResourceEngine(ResourceEngine):

    def init_resource(self):
        self.stack_group.add_new_boto_stack(
            self.aws_region,
            self.resource,
            IoTPolicyBotoStack,
        )

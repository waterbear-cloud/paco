import paco.cftemplates
from paco.application.res_engine import ResourceEngine

class IoTPolicyResourceEngine(ResourceEngine):

    def init_resource(self):
        iotpolicy_ctl = self.paco_ctx.get_controller('IoTPolicy')
        iotpolicy_ctl.add_iotpolicy(
            self.account_ctx,
            self.aws_region,
            self.resource
        )

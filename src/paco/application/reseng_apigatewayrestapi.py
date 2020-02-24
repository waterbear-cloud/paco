import paco.cftemplates
from paco.application.res_engine import ResourceEngine


class ApiGatewayRestApiResourceEngine(ResourceEngine):

    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.ApiGatewayRestApi,
            stack_tags=self.stack_tags,
        )

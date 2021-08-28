from paco import cftemplates
from paco.application.res_engine import ResourceEngine


class WAFWebACLResourceEngine(ResourceEngine):
    def init_resource(self):

        if self.resource.scope == "CLOUDFRONT":
            self.aws_region = 'us-east-1'

        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.waf.WAFWebACL,
            stack_tags=self.stack_tags,
        )

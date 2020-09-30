from paco import cftemplates
from paco.application.res_engine import ResourceEngine


class CognitoUserPoolResourceEngine(ResourceEngine):
    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.CognitoUserPool,
            stack_tags=self.stack_tags,
        )

class CognitoIdentityPoolResourceEngine(ResourceEngine):
    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.CognitoIdentityPool,
            stack_tags=self.stack_tags,
        )

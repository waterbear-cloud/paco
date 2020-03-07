import paco.cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class S3BucketResourceEngine(ResourceEngine):

    def init_resource(self):
        s3_ctl = self.paco_ctx.get_controller('S3')
        # If an account was not set, use the network default
        if self.resource.account == None:
            account_ctx = self.account_ctx
        else:
            account_ctx = self.paco_ctx.get_account_context(account_ref=self.resource.account)
        s3_ctl.init_context(
            account_ctx,
            self.aws_region,
            self.resource.paco_ref_parts,
            self.stack_group,
            self.stack_tags,
        )
        s3_ctl.add_bucket(self.resource)

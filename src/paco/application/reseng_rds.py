import paco.cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class DBParameterGroupResourceEngine(ResourceEngine):

    def init_resource(self):
        aws_name = '-'.join([self.grp_id, self.res_id])
        paco.cftemplates.DBParameterGroup(
            self.paco_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.grp_id,
            self.resource,
            self.resource.paco_ref_parts
        )

class RDSMysqlResourceEngine(ResourceEngine):

    def init_resource(self):
        # RDS Mysql CloudFormation
        aws_name = '-'.join([self.grp_id, self.res_id])
        paco.cftemplates.RDS(
            self.paco_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.app_id,
            self.grp_id,
            self.res_id,
            self.resource,
            self.resource.paco_ref_parts
        )

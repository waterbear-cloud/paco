from paco.application.res_engine import ResourceEngine
import paco.cftemplates


class DBParameterGroupResourceEngine(ResourceEngine):
    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.DBParameterGroup,
            stack_tags=self.stack_tags,
        )

class DBClusterParameterGroupResourceEngine(ResourceEngine):
    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.DBClusterParameterGroup,
            stack_tags=self.stack_tags,
        )

class RDSPostgresqlResourceEngine(ResourceEngine):
    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.RDS,
            stack_tags=self.stack_tags,
        )

class RDSMysqlResourceEngine(ResourceEngine):
    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.RDS,
            stack_tags=self.stack_tags,
        )

class RDSMysqlAuroraResourceEngine(ResourceEngine):
    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.RDSAurora,
            stack_tags=self.stack_tags,
        )

class RDSPostgresqlAuroraResourceEngine(ResourceEngine):
    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.RDSAurora,
            stack_tags=self.stack_tags,
        )

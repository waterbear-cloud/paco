from paco.application.res_engine import ResourceEngine
import paco.cftemplates


class LBClassicResourceEngine(ResourceEngine):

    def init_resource(self):
        elb_config = self.resource[res_id]
        aws_name = '-'.join([self.grp_id, self.res_id])
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.ELB,
            stack_tags=self.stack_tags,
            extra_context={
                'env_ctx': self.env_ctx,
                'app_name': self.app.name,
            }
        )

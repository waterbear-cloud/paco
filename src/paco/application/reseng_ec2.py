from paco.application.res_engine import ResourceEngine
import paco.cftemplates


class EC2ResourceEngine(ResourceEngine):

    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.EC2,
            stack_tags=self.stack_tags,
            # ToDo: remove old-school use of env_ctx.netenv_id
            extra_context={
                'netenv_name': self.env_ctx.netenv_id,
                'env_name': self.env_name,
                'app_name': self.app_id,
            },
        )

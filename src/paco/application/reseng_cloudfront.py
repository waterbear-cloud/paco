import paco.cftemplates
from paco.application.res_engine import ResourceEngine


class CloudFrontResourceEngine(ResourceEngine):

    def init_resource(self):
        # Every factory is a CloudFront Stack
        for factory_name, factory_config in self.resource.factory.items():
            support_resource_ref_ext = 'factory.' + factory_name
            self.resource.domain_aliases = factory_config.domain_aliases
            self.resource.viewer_certificate.certificate = factory_config.viewer_certificate.certificate

            # set resolve_ref_obj for look-ups
            self.resource.viewer_certificate.resolve_ref_obj = self.app_engine
            factory_config.viewer_certificate.resolve_ref_obj = self.app_engine
            factory_config.resolve_ref_obj = self.app_engine

            # CloudFront CloudFormation
            self.stack_group.add_new_stack(
                self.aws_region,
                self.resource,
                paco.cftemplates.CloudFront,
                stack_tags=self.stack_tags,
                extra_context={'factory_name': factory_name},
                support_resource_ref_ext=support_resource_ref_ext,
            )

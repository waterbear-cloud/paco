import paco.cftemplates
from paco.application.res_engine import ResourceEngine
from paco.stack import StackOrder


class CloudFrontResourceEngine(ResourceEngine):

    def init_resource(self):
        for factory_name, factory_config in self.resource.factory.items():
            support_resource_ref_ext = 'factory.' + factory_name
            cloudfront_config_ref = self.resource.paco_ref_parts + '.' + support_resource_ref_ext
            self.resource.domain_aliases = factory_config.domain_aliases
            self.resource.viewer_certificate.certificate = factory_config.viewer_certificate.certificate

            # Create Certificate in us-east-1 because that is where CloudFront lives.
            acm_ctl = self.paco_ctx.get_controller('ACM')
            cert_group_id = cloudfront_config_ref + '.viewer_certificate'
            cert_group_id = cert_group_id.replace(self.aws_region, 'us-east-1')
            cert_config = self.paco_ctx.get_ref(self.resource.viewer_certificate.certificate)
            acm_ctl.add_certificate_config(
                self.account_ctx,
                'us-east-1',
                cert_group_id,
                'viewer_certificate',
                cert_config
            )
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

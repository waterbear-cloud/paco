from paco.application.res_engine import ResourceEngine
from paco.stack.botostack import BotoStack
from paco.aws_api.acm import DNSValidatedACMCertClient
import time


class ACMBotoStack(BotoStack):

    def init(self):
        self.cert_config_map = {}
        self.cert_config_list = []
        self.register_stack_output_config(self.stack_ref + '.arn', 'ViewerCertificateArn')
        self.cert_arn_cache = None

    def get_outputs_value(self, key):
        if self.cert_arn_cache != None:
            return self.cert_arn_cache

        acm_client = DNSValidatedACMCertClient(
            self.account_ctx,
            self.resource.domain_name,
            self.aws_region,
        )
        cert_arn = acm_client.get_certificate_arn()
        if cert_arn == None:
            self.provision()
            cert_arn = acm_client.get_certificate_arn()
        if self.resource.external_resource == False:
            acm_client.wait_for_certificate_validation(cert_arn)
        return cert_arn

    def provision(self):
        """
        Creates a certificate if one does not exists, then adds DNS validation records
        to the Route53 Hosted Zone.
        """
        cert_config = self.resource
        if cert_config.is_enabled() == False:
            return
        if cert_config.external_resource == True:
            return
        cert_domain = cert_config.domain_name
        acm_client = DNSValidatedACMCertClient(self.account_ctx, cert_domain, self.aws_region)

        # Create the certificate if it does not exists
        cert_arn = acm_client.get_certificate_arn()
        if cert_arn == None:
            action = 'Create'
        else:
            action = 'Cache'
        self.paco_ctx.log_action_col(
            'Provision',
            action,
            self.account_ctx.get_name() + '.' + self.aws_region,
            'boto3: ' + cert_config.domain_name + ': alt-names: {}'.format(
                cert_config.subject_alternative_names
            ),
            col_2_size=9
        )
        cert_arn = acm_client.request_certificate(
            cert_arn,
            cert_config.private_ca,
            cert_config.subject_alternative_names
        )
        self.cert_arn_cache = cert_arn
        # Private CA Certs are automatically validated. No need for DNS.
        if cert_config.private_ca == None:
            validation_records = None
            while validation_records == None:
                validation_records = acm_client.get_domain_validation_records(cert_arn)
                if len(validation_records) == 0 or 'ResourceRecord' not in validation_records[0]:
                    self.paco_ctx.log_action_col(
                        'Waiting',
                        'DNS',
                        self.account_ctx.get_name() + '.' + self.aws_region,
                        'DNS validation record: ' + cert_config.domain_name,
                        col_2_size=9
                    )
                    time.sleep(2)
                    validation_records = None
            acm_client.create_domain_validation_records(cert_arn)

class ACMResourceEngine(ResourceEngine):

    def init_resource(self):

        # create a BotoStack, initialize and return it
        acmstack = ACMBotoStack(
            self.paco_ctx,
            self.account_ctx,
            None, # do not need StackGroup?
            self.resource,
            aws_region=self.aws_region,
        )
        acmstack.init()
        self.resource.stack = acmstack

        # acm_ctl = self.paco_ctx.get_controller('ACM')
        # cert_group_id = self.resource.paco_ref_parts
        # acm_ctl.add_certificate_config(
        #     self.account_ctx,
        #     self.aws_region,
        #     cert_group_id,
        #     self.res_id,
        #     self.resource
        # )

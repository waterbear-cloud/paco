from paco.stack.botostack import BotoStack
from paco.aws_api.acm import DNSValidatedACMCertClient
import time


class ACMBotoStack(BotoStack):

    def init(self):
        "Prepare Resource State"
        self.register_stack_output_config(self.stack_ref + '.arn', 'ViewerCertificateArn')
        self.enabled = self.resource.is_enabled()

    @property
    def cert_aws_region(self):
        if self.resource.region != None:
            return self.resource.region
        else:
            return self.aws_region

    def get_outputs(self):
        "Get all Outputs of a Resource"
        acm_client = DNSValidatedACMCertClient(
            self.account_ctx,
            self.resource.domain_name,
            self.cert_aws_region,
        )
        cert_arn = acm_client.get_certificate_arn()
        return {'ViewerCertificateArn': cert_arn}

    def provision(self):
        """
        Creates a certificate if one does not exists, then adds DNS validation records
        to the Route53 Hosted Zone.
        """
        if not self.enabled:
            return
        if self.resource.external_resource == True:
            return
        acm_client = DNSValidatedACMCertClient(
            self.account_ctx,
            self.resource.domain_name,
            self.cert_aws_region
        )

        # Create the certificate if it does not exists
        cert_arn = acm_client.get_certificate_arn()
        if cert_arn == None:
            action = 'Create'
        else:
            action = 'Cache'
        self.paco_ctx.log_action_col(
            'Provision',
            action,
            self.account_ctx.get_name() + '.' + self.cert_aws_region,
            f'boto3: {self.resource.domain_name}: alt-names: {self.resource.subject_alternative_names}',
            col_2_size=9
        )
        cert_arn = acm_client.request_certificate(
            cert_arn,
            self.resource.private_ca,
            self.resource.subject_alternative_names
        )
        self.cert_arn_cache = cert_arn
        # Private CA Certs are automatically validated. No need for DNS.
        if self.resource.private_ca == None:
            validation_records = None
            while validation_records == None:
                validation_records = acm_client.get_domain_validation_records(cert_arn)
                if len(validation_records) == 0 or 'ResourceRecord' not in validation_records[0]:
                    self.paco_ctx.log_action_col(
                        'Waiting',
                        'DNS',
                        self.account_ctx.get_name() + '.' + self.cert_aws_region,
                        'DNS validation record: ' + self.resource.domain_name,
                        col_2_size=9
                    )
                    time.sleep(2)
                    validation_records = None
            acm_client.create_domain_validation_records(cert_arn)
        if self.resource.external_resource == False:
            acm_client.wait_for_certificate_validation(cert_arn)


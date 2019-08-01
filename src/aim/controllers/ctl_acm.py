import click
import os
import time
from aim.aws_api.acm import DNSValidatedACMCertClient
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.controllers.controllers import Controller


class ACMController(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Service",
                         "ACM")

        self.cert_config_map = {}
        self.cert_config_list = []

        #self.aim_ctx.log("ACM Service: Configuration: %s" % (name))

    def init(self, controller_args):
        pass

    def validate(self):
        #if self.config.enabled() == False:
        #    print("ACM Service: validate: disabled")
        #    return
        pass

    def provision(self):
        #print("ACM Service Controller: provision")
        #if self.config.enabled() == False:
        #    print("ACM Service: provision: disabled")
        #    return
#        print("ACM Provision")
        # self.validate()
        for acm_config in self.cert_config_list:
            cert_config = acm_config['config']
            cert_domain = cert_config.domain_name
            #aws_session = acm_config.account_ctx.get_session()
            acm_client = DNSValidatedACMCertClient(acm_config['account_ctx'], cert_domain)
            #print("Alternate sert name: %s" % (cert_config.subject_alternative_names))
            cert_arn = acm_client.request_certificate(cert_config.subject_alternative_names)
            #           print("Cert arn: %s" % (cert_arn))
            validation_records = None
            while validation_records == None:
                validation_records = acm_client.get_domain_validation_records(cert_arn)
                #                print("Validation records")
                #                print(validation_records)
                if 'ResourceRecord' not in validation_records[0]:
                    print("Waiting for DNS Validation records...")
                    time.sleep(1)
                    validation_records = None
#                    else:
#                        print("...received validation records")

            #print("Creating validation records in Route53")
            acm_client.create_domain_validation_records(cert_arn)


    def get_cert_config(self, group_id, cert_id):
        for config in self.cert_config_map[group_id]:
            if config['id'] == cert_id:
                return config
        return None

    def resolve_ref(self, ref):
        if ref.resource_ref == 'arn':
            group_id = '.'.join(ref.parts[:-1])
            cert_id = ref.parts[-2]
            res_config = self.get_cert_config(group_id, cert_id)
            acm_client = DNSValidatedACMCertClient(res_config['account_ctx'], ref.resource.domain_name)
            if acm_client:
                cert_arn = acm_client.get_certificate_arn()
                if cert_arn == None:
                    self.provision()
                    cert_arn = acm_client.get_certificate_arn()
                acm_client.wait_for_certificate_validation( cert_arn )
                # print("Certificate ARN: " + cert_domain + ": " + cert_arn)
                return cert_arn
            else:
                raise StackException(AimErrorCode.Unknown)
        raise StackException(AimErrorCode.Unknown)

    def add_certificate_config(self, account_ctx, group_id, cert_id, cert_config):
        # print("Add Certificate Config: " + group_id + " " + cert_id)
        if group_id not in self.cert_config_map.keys():
            self.cert_config_map[group_id] = []

        map_config = {
            'group_id': group_id,
            'id': cert_id,
            'config': cert_config,
            'account_ctx': account_ctx
        }
        self.cert_config_map[group_id].append(map_config)
        self.cert_config_list.append(map_config)
        cert_config.resolve_ref_obj = self
from botocore.config import Config
import tldextract
from . import aws_helpers
import time


class DNSValidatedACMCertClient():

    def __init__(self, account_ctx, domain, region):
        self.region = region
        self.account_ctx = account_ctx
        self.domain = domain

    @property
    def acm_client(self):
        if hasattr(self, '_acm_client') == False:
            self._acm_client = self.account_ctx.get_aws_client('acm', self.region)
        return self._acm_client

    @property
    def route_53_client(self):
        if hasattr(self, '_route_53_client') == False:
            self._route_53_client = self.account_ctx.get_aws_client(
                'route53',
                client_config=Config(retries={'max_attempts': 10}))
        return self._route_53_client

    def get_certificate_arn_from_response(self, response):
        """Given an ACM Boto response, return the ACM Certificate ARN."""
        return response.get('CertificateArn')

    def get_certificate_arn(self):
        list_certs_args = {}
        while True:
            cert_list = self.acm_client.list_certificates(**list_certs_args)
            if len(cert_list['CertificateSummaryList']) == 0:
                return None
            for cert_item in cert_list['CertificateSummaryList']:
                if cert_item['DomainName'] == self.domain:
                    return cert_item['CertificateArn']
            if 'NextToken' in cert_list.keys():
                list_certs_args = {'NextToken': cert_list['NextToken'] }
                continue
            break
        return None

    def request_certificate(self, cert_arn, private_ca_arn, subject_alternative_names=[]):
        """Given a list of (optional) subject alternative names, request a certificate
        and return the certificate ARN.
        """
        if cert_arn == None:
            cert_dict = {
                'DomainName': self.domain,
                'ValidationMethod': 'DNS',
            }
            if private_ca_arn != None:
                cert_dict['CertificateAuthorityArn'] = private_ca_arn

            if len(subject_alternative_names) > 0:
                cert_dict['SubjectAlternativeNames'] = subject_alternative_names

            response = self.acm_client.request_certificate(**cert_dict)

            if aws_helpers.response_succeeded(response):
                return self.get_certificate_arn_from_response(response)
            else:
                return None
        else:
            return cert_arn

    def get_certificate_status(self, certificate_arn):
        return self.acm_client.describe_certificate(CertificateArn=certificate_arn)['Certificate']['Status']

    def wait_for_certificate_validation(self, certificate_arn, sleep_time=5, timeout=600):
        status = self.get_certificate_status(certificate_arn)
        elapsed_time = 0
        while status == 'PENDING_VALIDATION':
            print("Waiting for certificate validation: timeout in %d seconds: %s" % (timeout-elapsed_time, certificate_arn))
            if elapsed_time > timeout:
                raise Exception('Timeout ({}s) reached for certificate validation'.format(timeout))
            time.sleep(sleep_time)
            status = self.get_certificate_status(certificate_arn)
            elapsed_time += sleep_time

    def get_domain_validation_records(self, arn):
        """Return the domain validation records from the describe_certificate call for our certificate"""
        certificate_metadata = self.acm_client.describe_certificate(
            CertificateArn=arn)
        return certificate_metadata.get('Certificate', {}).get(
            'DomainValidationOptions', [])

    def get_hosted_zone_id(self, validation_dns_record):
        """Return the HostedZoneId of the zone tied to the root domain of the domain the
        to protect (e.g. given www.cnn.com, return cnn.com) if it exists in Route53.
        """

        def get_domain_from_host(validation_dns_record):
            """ Given an FQDN, return the domain
                portion of a host
            """
            domain_tld_info = tldextract.extract(validation_dns_record)
            return "%s.%s" % (domain_tld_info.domain, domain_tld_info.suffix)

        def domain_matches_hosted_zone(domain, zone):
            return zone.get('Name') == "%s." % (domain)

        def get_zone_id_from_id_string(zone_id_string):
            return zone_id_string.split('/')[-1]

        domain_tld_info = tldextract.extract(validation_dns_record)
        hosted_zone_subdomain = domain_tld_info.subdomain
        while True:
            hosted_zone_subdomain_list = hosted_zone_subdomain.split(".",1)
            hosted_zone_domain = '.'.join([
                domain_tld_info.domain,
                domain_tld_info.suffix
            ])
            if len(hosted_zone_subdomain_list) > 1:
                hosted_zone_subdomain = hosted_zone_subdomain.split(".", 1)[1]
                hosted_zone_domain = '.'.join([
                    hosted_zone_subdomain,
                    domain_tld_info.domain,
                    domain_tld_info.suffix
                ])
            list_hosted_zones_paginator = self.route_53_client.get_paginator('list_hosted_zones')
            route53_zones = list_hosted_zones_paginator.paginate().build_full_result()
            for zone in route53_zones.get('HostedZones'):
                if domain_matches_hosted_zone(hosted_zone_domain, zone) == True:
                    return get_zone_id_from_id_string(zone.get('Id'))
            if len(hosted_zone_subdomain_list) == 1:
                return None
        return None

    def get_resource_record_data(self, r):
        """
        Given a ResourceRecord dictionary from an ACM certificate response,
        return the type, name and value of the record.
        """
        return (r.get('Type'), r.get('Name'), r.get('Value'))

    def create_dns_record_set(self, record):
        """Given a HostedZoneId and a list of domain validation records, create a
        DNS record set to send to Route 53.
        """
        record_type, record_name, record_value = self.get_resource_record_data(
            record.get('ResourceRecord'))
        return {
            'Action': 'UPSERT',
            'ResourceRecordSet': {
                'Name': record_name,
                'Type': record_type,
                'ResourceRecords': [{
                    'Value': record_value
                }],
                'TTL': 300,
            }
        }

    def remove_duplicate_upsert_records(self, original_list):
        unique_list = []
        [unique_list.append(obj) for obj in original_list if obj not in unique_list]
        return unique_list

    def create_domain_validation_records(self, arn):
        """Given an ACM certificate ARN return the response"""
        domain_validation_records = self.get_domain_validation_records(arn)
        changes = [
            self.create_dns_record_set(record)
            for record in domain_validation_records
        ]
        unique_changes = self.remove_duplicate_upsert_records(changes)
        for change in unique_changes:
            record_name = change.get('ResourceRecordSet').get('Name')
            hosted_zone_id = self.get_hosted_zone_id(record_name)
            if hosted_zone_id == None:
                print("ACM: Unable to get Hosted Zone id for: {}".format(record_name))
                continue
            response = self.route_53_client.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                'Changes': [change]
            })
            if not aws_helpers.response_succeeded(response):
                print("Failed to create Route53 record set: {}".format(response))
            #else:
            #    print("Successfully created Route 53 record set for {}".format(record_name))

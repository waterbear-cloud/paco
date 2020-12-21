from paco.cftemplates.cftemplates import StackTemplate
from paco.models import references
from paco import utils
import os
import troposphere


class Route53RecordSet(StackTemplate):
    def __init__(
        self,
        stack,
        paco_ctx,
        record_set_name,
        record_set_config,
    ):
        if references.is_ref(record_set_name) == True:
            record_set_name = paco_ctx.get_ref(record_set_name)
        super().__init__(stack, paco_ctx)

        hosted_zone_is_private = False
        if references.is_ref(record_set_config['dns'].hosted_zone):
            hosted_zone_is_private = self.paco_ctx.get_ref(record_set_config['dns'].hosted_zone+'.private_hosted_zone')
        aws_name = 'RecordSet'
        if hosted_zone_is_private == True:
            aws_name = aws_name+'-Private'
        self.set_aws_name(aws_name, record_set_name)

        # Troposphere Template Initialization
        self.init_template('Route53 RecordSet: ' + record_set_name)

        # Parameters
        hosted_zone_id = record_set_config['dns'].hosted_zone
        private_hosted_zone_id = record_set_config['dns'].private_hosted_zone
        if references.is_ref(hosted_zone_id):
            hosted_zone_id = hosted_zone_id + '.id'

        if private_hosted_zone_id != None and references.is_ref(private_hosted_zone_id):
            private_hosted_zone_id = private_hosted_zone_id + '.id'

        hosted_zone_id_param = self.create_cfn_parameter(
            param_type='String',
            name='HostedZoneId',
            description='Record Set Hosted Zone Id',
            value=hosted_zone_id,
        )

        if private_hosted_zone_id != None:
            private_hosted_zone_id_param = self.create_cfn_parameter(
                param_type='String',
                name='PrivateHostedZoneId',
                description='Record Set Hosted Zone Id',
                value=private_hosted_zone_id,
            )

        record_set_type = record_set_config['record_set_type']
        if record_set_config['record_set_type'] == 'Alias':
            record_set_type = 'A'

        record_set_dict = {
            'HostedZoneId': troposphere.Ref(hosted_zone_id_param),
            'Name': record_set_name,
            'Type': record_set_type
        }

        # Alias
        if record_set_config['record_set_type'] == "Alias":
            alias_hosted_zone_id_param = self.create_cfn_parameter(
                param_type='String',
                name='AliasHostedZoneId',
                description='Hosted Zone Id for the A Alias',
                value=record_set_config['alias_hosted_zone_id'],
            )
            alias_dns_name_param = self.create_cfn_parameter(
                param_type='String',
                name='AliasDNSName',
                description='DNS Name for the A Alias',
                value=record_set_config['alias_dns_name'],
            )
            record_set_dict['AliasTarget'] = {
                'DNSName': troposphere.Ref(alias_dns_name_param),
                'HostedZoneId': troposphere.Ref(alias_hosted_zone_id_param)
            }
        else:
            record_set_dict['TTL'] = record_set_config['dns'].ttl
            record_set_dict['ResourceRecords'] = []
            for resource_record in record_set_config['resource_records']:
                # legacy_flag: aim_name_2019_11_28 - hash with aim.ref instead of paco.ref
                hash_name = resource_record
                if self.paco_ctx.legacy_flag('aim_name_2019_11_28') == True:
                    hash_name = 'aim' + hash_name[4:]
                record_hash = utils.md5sum(str_data=hash_name)
                resource_record_param = self.create_cfn_parameter(
                    param_type='String',
                    name='ResourceRecord' + record_hash,
                    description='Resource Record: ' + hash_name,
                    value=resource_record,
                )
                record_set_dict['ResourceRecords'].append(troposphere.Ref(resource_record_param))

        record_set_res = troposphere.route53.RecordSetType.from_dict(
            self.create_cfn_logical_id_join(['RecordSet']),
            record_set_dict
        )
        self.template.add_resource(record_set_res)

        # Private Hosted Zone
        if private_hosted_zone_id != None:
            record_set_dict['HostedZoneId'] = troposphere.Ref(private_hosted_zone_id_param)
            private_record_set_res = troposphere.route53.RecordSetType.from_dict(
                self.create_cfn_logical_id_join(['PrivateRecordSet']),
                record_set_dict
            )
            self.template.add_resource(private_record_set_res)

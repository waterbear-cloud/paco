import os
import troposphere
#import troposphere.<resource>

from paco.cftemplates.cftemplates import CFTemplate
from paco.models import references
from paco import utils


class Route53RecordSet(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,

        record_set_name,
        record_set_config,
        config_ref):

        if references.is_ref(record_set_name) == True:
            record_set_name = paco_ctx.get_ref(record_set_name)

        # ---------------------------------------------------------------------------
        # CFTemplate Initialization
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=record_set_config['enabled'],
            config_ref=config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags,
            change_protected=record_set_config['change_protected']
        )
        self.set_aws_name('RecordSet', record_set_name)

        # ---------------------------------------------------------------------------
        # Troposphere Template Initialization
        self.init_template('Route53 RecordSet: ' + record_set_name)

        # ---------------------------------------------------------------------------
        # Parameters
        hosted_zone_id = record_set_config['dns'].hosted_zone
        if references.is_ref(record_set_config['dns'].hosted_zone):
            hosted_zone_id = record_set_config['dns'].hosted_zone + '.id'
        hosted_zone_id_param = self.create_cfn_parameter(
            param_type='String',
            name='HostedZoneId',
            description='Record Set Hosted Zone Id',
            value=hosted_zone_id,
            use_troposphere=True,
            troposphere_template=self.template
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
                use_troposphere=True,
                troposphere_template=self.template
                )

            alias_dns_name_param = self.create_cfn_parameter(
                param_type='String',
                name='AliasDNSName',
                description='DNS Name for the A Alias',
                value=record_set_config['alias_dns_name'],
                use_troposphere=True,
                troposphere_template=self.template
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
                    use_troposphere=True,
                    troposphere_template=self.template
                )
                record_set_dict['ResourceRecords'].append(troposphere.Ref(resource_record_param))

        record_set_res = troposphere.route53.RecordSetType.from_dict(
            self.create_cfn_logical_id_join(['RecordSet']),
            record_set_dict
        )
        self.template.add_resource(record_set_res)

        # Generate the Template
        self.set_template(self.template.to_yaml())


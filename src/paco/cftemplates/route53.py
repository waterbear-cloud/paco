from paco.cftemplates.cftemplates import StackTemplate


class Route53(StackTemplate):
    def __init__(self, stack, paco_ctx):
        route53_config = stack.resource
        config_ref = route53_config.paco_ref_parts
        super().__init__(
            stack,
            paco_ctx,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
        )
        self.set_aws_name('HostedZones')

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Route53 Hosted Zone'

Resources:
  EmptyTemplatePlaceholder:
    Type: AWS::CloudFormation::WaitConditionHandle
{0[resources_yaml]:s}

{0[outputs_yaml]:s}
"""
        template_table = {
            'resources_yaml': "",
            'outputs_yaml': ""
        }

        hosted_zone_fmt = """
  {0[cf_resource_name_prefix]:s}HostedZone:
    Type: AWS::Route53::HostedZone
    Properties:
      Name: {0[domain]:s}

  {0[record_set_group]:s}
"""

        record_set_group_fmt = """
  {0[cf_resource_name_prefix]:s}RecordSetGroup:
    Type: AWS::Route53::RecordSetGroup
    Properties:
      HostedZoneId: !Ref {0[cf_resource_name_prefix]:s}HostedZone
      RecordSets:"""

        record_set_fmt = """
        - Name: {0[domain]:s}
          Type: {0[type]:s}
          TTL: {0[ttl]:d}
          AliasTarget: {0[alias_target]:s}
          ResourceRecords: {0[resource_records]:s}
"""

        outputs_fmt = """
  {0[cf_resource_name_prefix]:s}HostedZoneId:
    Value: !Ref {0[cf_resource_name_prefix]:s}HostedZone
"""

        hosted_zone_table = {
            'cf_resource_name_prefix': None,
            'domain': None,
            'record_set_group': None
        }

        record_sets_table = {
            'domain': None,
            'type': None,
            'ttl': None,
            'resource_records': None,
            'alias_target': None
        }

        resource_record_fmt = """
            - {0[resource_record]:s}
"""

        resource_records_table = {
            'resource_record': None
        }

        resources_yaml = ""
        outputs_yaml = ""
        records_set_yaml = ""

        account_zones_enabled = False
        for zone_id in route53_config.get_zone_ids(account_name=stack.account_ctx.get_name()):
            zone_config = route53_config.hosted_zones[zone_id]
            if zone_config.is_enabled() == False:
                continue
            account_zones_enabled = True
            res_name_prefix = self.gen_cf_logical_name(zone_id, '_')
            hosted_zone_table['cf_resource_name_prefix'] = res_name_prefix
            hosted_zone_table['domain'] = zone_config.domain_name
            if zone_config.has_record_sets():
                hosted_zone_table['record_set_group'] = record_set_group_fmt.format(hosted_zone_table)
            else:
                hosted_zone_table['record_set_group'] = ""

            # TODO: Uncomment this when RecordSets have been integrated into the model
            #for record_set_id in zone_config.record_sets.keys():
            #    record_sets_table.clear()
            #    record_sets_table['domain'] = route53_config.get_record_set_domain_name(zone_id, record_set_id)
            #    record_sets_table['type'] = route53_config.get_record_set_type(zone_id, record_set_id)
            #    if route53_config.record_set_has_alias_target(zone_id, record_set_id):
            #        record_sets_table['ttl'] = "!Ref 'AWS::NoValue'"
            #        record_sets_table['resource_records'] = "!Ref 'AWS::NoValue'"
            #        record_sets_table['alias_target'] = route53_config.get_record_set_alias_target(zone_id, record_set_id)
            #    else:
            #        record_sets_table['alias_target'] = "!Ref 'AWS::NoValue'"
            #        record_sets_table['ttl'] = route53_config.get_record_set_ttl(zone_id, record_set_id)
            #        record_sets_table['resource_records'] = ""
            #        for resource_record in route53_config.get_record_set_resource_records(zone_id, record_set_id):
            #            resource_records_table.clear()
            #            resource_records_table['resource_record'] = resource_record
            #           record_sets_table['resource_records'] += resource_record_fmt.format(resource_records_table)

            #    hosted_zone_table['record_set_group'] += record_set_fmt.format(record_sets_table)
            zone_config_ref = '.'.join([config_ref, zone_id])
            self.stack.register_stack_output_config(zone_config_ref + '.id', res_name_prefix + 'HostedZoneId')
            resources_yaml += hosted_zone_fmt.format(hosted_zone_table)
            outputs_yaml += outputs_fmt.format(hosted_zone_table)

        template_table['resources_yaml'] = resources_yaml
        if outputs_yaml != '':
            outputs_yaml = 'Outputs:\n' + outputs_yaml
        template_table['outputs_yaml'] = outputs_yaml

        self.enabled = account_zones_enabled
        self.set_template(template_fmt.format(template_table))



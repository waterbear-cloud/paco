import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from io import StringIO
from enum import Enum


class Route53(CFTemplate):
    def __init__(self, aim_ctx, account_ctx, route53_config):
        #aim_ctx.log("Route53 CF Template init")

        super().__init__(aim_ctx,
                         account_ctx,
                         config_ref=None,
                         aws_name="HostedZones",
                         iam_capabilities=["CAPABILITY_NAMED_IAM"])


        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Route53 Hosted Zone'

#Parameters:
#{0[parameters_yaml]:s}

Resources:
{0[resources_yaml]:s}

Outputs:
{0[outputs_yaml]:s}
"""
        template_table = {
            'parameters_yaml': "",
            'resources_yaml': "",
            'outputs_yaml': ""
        }


#        params_fmt ="""
#  {0[?_name]:s}:
#    Type: String
#    Description: 'The path associated with the {0[role_path_param_name]:s} IAM Role'
#"""

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

        parameters_yaml = ""
        resources_yaml = ""
        outputs_yaml = ""
        records_set_yaml = ""

        for zone_id in route53_config.get_zone_ids(account_name=account_ctx.get_name()):
            zone_config = route53_config.hosted_zones[zone_id]
            hosted_zone_table['cf_resource_name_prefix'] = self.gen_cf_logical_name(zone_id, '_')
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

            resources_yaml += hosted_zone_fmt.format(hosted_zone_table)
            outputs_yaml += outputs_fmt.format(hosted_zone_table)

        template_table['parameters_yaml'] = parameters_yaml
        template_table['resources_yaml'] = resources_yaml
        template_table['outputs_yaml'] = outputs_yaml
        self.set_template(template_fmt.format(template_table))

    def validate(self):
        #self.aim_ctx.log("Validating Route53 Template")
        super().validate()

    def get_outputs_key_from_ref(self, aim_ref):
        ref_dict = self.aim_ctx.parse_ref(aim_ref)

        output_key = self.gen_cf_logical_name(ref_dict['ref_parts'][1], '_') + "HostedZoneId"
        return output_key

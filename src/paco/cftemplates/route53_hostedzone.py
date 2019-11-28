import troposphere
import troposphere.route53

from paco.cftemplates.cftemplates import CFTemplate

class Route53HostedZone(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        zone_config,
        config_ref):
        #paco_ctx.log("Route53 CF Template init")
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=zone_config.is_enabled(),
            config_ref=config_ref,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('HostedZone', zone_config.name)

        self.init_template('Route53 Hosted Zone: ' + zone_config.domain_name)

        self.paco_ctx.log_action_col("Init", "Route53", "Hosted Zone", "{}".format(zone_config.domain_name))

        if zone_config.external_resource != None and zone_config.external_resource.is_enabled():
            hosetd_zone_id_output_value = zone_config.external_resource.hosted_zone_id
            nameservers_output_value = ','.join(zone_config.external_resource.nameservers)
        else:
            hosted_zone_res = troposphere.route53.HostedZone(
                title='HostedZone',
                template=self.template,
                Name=zone_config.domain_name
            )
            hosetd_zone_id_output_value = troposphere.Ref(hosted_zone_res)
            nameservers_output_value = troposphere.Join(',', troposphere.GetAtt(hosted_zone_res, 'NameServers'))


        self.template.add_output(
            troposphere.Output(
                title = 'HostedZoneId',
                Value = hosetd_zone_id_output_value
            )
        )
        self.template.add_output(
            troposphere.Output(
                title = 'HostedZoneNameServers',
                Value = nameservers_output_value
            )
        )
        self.register_stack_output_config(config_ref+'.id', 'HostedZoneId')
        self.register_stack_output_config(config_ref+'.name_servers', 'HostedZoneNameServers')

        if len(zone_config.record_sets) > 0:
            record_set_list = []
            for record_set_config in zone_config.record_sets:
                record_set_res = troposphere.route53.RecordSet(
                    Name=record_set_config.record_name,
                    Type=record_set_config.type,
                    TTL=record_set_config.ttl,
                    ResourceRecords=record_set_config.resource_records
                )
                record_set_list.append(record_set_res)

            group_res = troposphere.route53.RecordSetGroup(
                title='RecordSetGroup',
                template=self.template,
                HostedZoneId=troposphere.Ref(hosted_zone_res),
                RecordSets=record_set_list
            )
            group_res.DependsOn = hosted_zone_res


        self.set_template(self.template.to_yaml())



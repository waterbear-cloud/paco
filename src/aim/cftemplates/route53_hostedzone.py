import troposphere
import troposphere.route53

from aim.cftemplates.cftemplates import CFTemplate

class Route53HostedZone(CFTemplate):
    def __init__(
        self,
        aim_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        zone_config,
        config_ref):
        #aim_ctx.log("Route53 CF Template init")
        super().__init__(
            aim_ctx,
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

        self.aim_ctx.log_action_col("Init", "Route53", "Hosted Zone", "{}".format(zone_config.domain_name))

        hosted_zone_res = troposphere.route53.HostedZone(
            title='HostedZone',
            template=self.template,
            Name=zone_config.domain_name
        )

        self.template.add_output(
            troposphere.Output(
                title = 'HostedZoneId',
                Value = troposphere.Ref(hosted_zone_res)
            )
        )
        self.template.add_output(
            troposphere.Output(
                title = 'HostedZoneNameServers',
                Value = troposphere.Join(',', troposphere.GetAtt(hosted_zone_res, 'NameServers'))
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



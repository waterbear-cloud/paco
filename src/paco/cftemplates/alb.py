import os
import troposphere
import troposphere.elasticloadbalancingv2
from paco.cftemplates.cftemplates import CFTemplate
from paco.cftemplates.cftemplates import StackOutputParam
from paco.models.references import Reference, get_model_obj_from_ref
from io import StringIO
from enum import Enum
from pprint import pprint


class ALB(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        env_ctx,
        app_id,
        grp_id,
        alb_config
    ):
        self.env_ctx = env_ctx
        self.config_ref = alb_config.paco_ref_parts
        segment_stack = self.env_ctx.get_segment_stack(alb_config.segment)
        super().__init__(
            paco_ctx=paco_ctx,
            account_ctx=account_ctx,
            aws_region=aws_region,
            enabled=alb_config.is_enabled(),
            config_ref=alb_config.paco_ref_parts,
            stack_group=stack_group,
            stack_tags=stack_tags,
            environment_name=self.env_ctx.env_id,
            change_protected=alb_config.change_protected
        )
        self.set_aws_name('ALB', grp_id, alb_config.name)

        # Init Troposphere template
        self.init_template('Application Load Balancer')
        if not alb_config.is_enabled():
            self.set_template(self.template.to_yaml())
            return

        # Parameters
        if alb_config.is_enabled():
            alb_enable = 'true'
        else:
            alb_enable = 'false'

        alb_is_enabled_param = self.create_cfn_parameter(
            param_type='String',
            name='ALBEnabled',
            description='Enable the ALB in this template',
            value=alb_enable,
            use_troposphere=True,
            troposphere_template=self.template
        )
        vpc_stack = self.env_ctx.get_vpc_stack()
        vpc_param = self.create_cfn_parameter(
            param_type='String',
            name='VPC',
            description='VPC ID',
            value=StackOutputParam('VPC', vpc_stack, 'VPC', self),
            use_troposphere=True,
            troposphere_template=self.template
        )
        alb_region = env_ctx.region
        alb_hosted_zone_id_param = self.create_cfn_parameter(
            param_type='String',
            name='ALBHostedZoneId',
            description='The Regonal AWS Route53 Hosted Zone ID',
            value=self.lb_hosted_zone_id('alb', alb_region),
            use_troposphere=True,
            troposphere_template=self.template
        )

        # 32 Characters max
        # <proj>-<env>-<app>-<alb.name>
        # TODO: Limit each name item to 7 chars
        # Name collision risk:, if unique identifying characrtes are truncated
        #   - Add a hash?
        #   - Check for duplicates with validating template
        load_balancer_name = self.create_resource_name_join(
            name_list=[self.env_ctx.netenv_id, self.env_ctx.env_id, app_id, grp_id, alb_config.name],
            separator='',
            camel_case=True,
            filter_id='EC2.ElasticLoadBalancingV2.LoadBalancer.Name'
        )
        load_balancer_name_param = self.create_cfn_parameter(
            param_type='String',
            name='LoadBalancerName',
            description='The name of the load balancer',
            value=load_balancer_name,
            use_troposphere=True,
            troposphere_template=self.template
        )
        scheme_param = self.create_cfn_parameter(
            param_type='String',
            min_length=1,
            max_length=128,
            name='Scheme',
            description='Specify internal to create an internal load balancer with a DNS name that resolves to private IP addresses or internet-facing to create a load balancer with a publicly resolvable DNS name, which resolves to public IP addresses.',
            value=alb_config.scheme,
            use_troposphere=True,
            troposphere_template=self.template
        )

        # Segment SubnetList is a Segment stack Output based on availability zones
        subnet_list_key = 'SubnetList' + str(self.env_ctx.availability_zones())
        subnet_list_param = self.create_cfn_parameter(
            param_type='List<AWS::EC2::Subnet::Id>',
            name='SubnetList',
            description='A list of subnets where the ALBs instances will be provisioned',
            value=StackOutputParam('SubnetList', segment_stack, subnet_list_key, self),
            use_troposphere=True,
            troposphere_template=self.template
        )
        security_group_list_param = self.create_cfn_ref_list_param(
            param_type='List<AWS::EC2::SecurityGroup::Id>',
            name='SecurityGroupList',
            description='A List of security groups to attach to the ALB',
            value=alb_config.security_groups,
            ref_attribute='id',
            use_troposphere=True,
            troposphere_template=self.template
        )
        idle_timeout_param = self.create_cfn_parameter(
            param_type='String',
            name='IdleTimeoutSecs',
            description='The idle timeout value, in seconds.',
            value=alb_config.idle_timeout_secs,
            use_troposphere=True,
            troposphere_template=self.template
        )

        # Conditions
        self.template.add_condition(
            "ALBIsEnabled",
            troposphere.Equals(troposphere.Ref(alb_is_enabled_param), "true")
        )

        # Resources

        # LoadBalancer
        load_balancer_logical_id = 'LoadBalancer'
        cfn_export_dict = {}
        cfn_export_dict['Name'] = troposphere.Ref(load_balancer_name_param)
        cfn_export_dict['Type'] = 'application'
        cfn_export_dict['Scheme'] = troposphere.Ref(scheme_param)
        cfn_export_dict['SecurityGroups'] = troposphere.Ref(security_group_list_param)
        cfn_export_dict['Subnets'] = troposphere.Ref(subnet_list_param)

        lb_attributes = [
            {'Key': 'idle_timeout.timeout_seconds', 'Value': troposphere.Ref(idle_timeout_param)}
        ]
        if alb_config.enable_access_logs:
            # ToDo: automatically create a bucket when access_logs_bucket is not set
            s3bucket = get_model_obj_from_ref(alb_config.access_logs_bucket, self.paco_ctx.project)
            lb_attributes.append(
                {'Key': 'access_logs.s3.enabled', 'Value': 'true'}
            )
            lb_attributes.append(
                {'Key': 'access_logs.s3.bucket', 'Value': s3bucket.get_bucket_name() }
            )
            if alb_config.access_logs_prefix:
                lb_attributes.append(
                    {'Key': 'access_logs.s3.prefix', 'Value': alb_config.access_logs_prefix}
                )

        cfn_export_dict['LoadBalancerAttributes'] = lb_attributes

        alb_resource = troposphere.elasticloadbalancingv2.LoadBalancer.from_dict(
            load_balancer_logical_id,
            cfn_export_dict
        )
        alb_resource.Condition = "ALBIsEnabled"
        self.template.add_resource(alb_resource)

        # Target Groups
        for target_group_name, target_group in sorted(alb_config.target_groups.items()):
            target_group_id = self.create_cfn_logical_id(target_group_name)
            target_group_logical_id = 'TargetGroup' + target_group_id
            cfn_export_dict = {}
            if self.paco_ctx.legacy_flag('target_group_name_2019_10_29') == True:
                name = self.create_resource_name_join(
                    name_list=[load_balancer_name, target_group_id], separator='',
                    camel_case=True, hash_long_names=True,
                    filter_id='EC2.ElasticLoadBalancingV2.TargetGroup.Name',
                )
            else:
                name = troposphere.Ref('AWS::NoValue')
            cfn_export_dict['Name'] = name
            cfn_export_dict['HealthCheckIntervalSeconds'] = target_group.health_check_interval
            cfn_export_dict['HealthCheckTimeoutSeconds'] = target_group.health_check_timeout
            cfn_export_dict['HealthyThresholdCount'] = target_group.healthy_threshold
            cfn_export_dict['HealthCheckPath'] = target_group.health_check_path
            cfn_export_dict['Port'] = target_group.port
            cfn_export_dict['Protocol'] = target_group.protocol
            cfn_export_dict['UnhealthyThresholdCount'] = target_group.unhealthy_threshold
            cfn_export_dict['TargetGroupAttributes'] = [
                {'Key': 'deregistration_delay.timeout_seconds', 'Value': str(target_group.connection_drain_timeout) }
            ]
            cfn_export_dict['Matcher'] = {'HttpCode': target_group.health_check_http_code }
            cfn_export_dict['VpcId'] = troposphere.Ref(vpc_param)
            target_group_resource = troposphere.elasticloadbalancingv2.TargetGroup.from_dict(
                target_group_logical_id,
                cfn_export_dict
            )
            self.template.add_resource(target_group_resource)

            # Target Group Outputs
            target_group_arn_output = troposphere.Output(
                title='TargetGroupArn' + target_group_id,
                Value=troposphere.Ref(target_group_resource)
            )
            self.template.add_output(target_group_arn_output)
            target_group_ref = '.'.join([alb_config.paco_ref_parts, 'target_groups', target_group_name])
            target_group_arn_ref = '.'.join([target_group_ref, 'arn'])
            self.register_stack_output_config(target_group_arn_ref, 'TargetGroupArn' + target_group_id)

            target_group_name_output = troposphere.Output(
                title='TargetGroupName' + target_group_id,
                Value=troposphere.GetAtt(target_group_resource, 'TargetGroupName')
            )
            self.template.add_output(target_group_name_output)
            target_group_name_ref = '.'.join([target_group_ref, 'name'])
            self.register_stack_output_config(target_group_name_ref, 'TargetGroupName' + target_group_id)

            target_group_fullname_output = troposphere.Output(
                title='TargetGroupFullName' + target_group_id,
                Value=troposphere.GetAtt(target_group_resource, 'TargetGroupFullName')
            )
            self.template.add_output(target_group_fullname_output)
            self.register_stack_output_config(target_group_ref + '.fullname', 'TargetGroupFullName' + target_group_id)

        # Listeners
        for listener_name, listener in alb_config.listeners.items():
            logical_listener_name = self.create_cfn_logical_id('Listener' + listener_name)
            cfn_export_dict = listener.cfn_export_dict

            # Listener - Default Actions
            if listener.redirect != None:
                action = {
                    'Type': 'redirect',
                    'RedirectConfig': {
                        'Port': str(listener.redirect.port),
                        'Protocol': listener.redirect.protocol,
                        'StatusCode': 'HTTP_301'
                    }
                }
            else:
                action = {
                    'Type': 'forward',
                    'TargetGroupArn': troposphere.Ref('TargetGroup' + listener.target_group)
                }
            cfn_export_dict['DefaultActions'] = [action]
            cfn_export_dict['LoadBalancerArn'] = troposphere.Ref(alb_resource)

            # Listener - SSL Certificates
            ssl_cert_param_obj_list = []
            if len(listener.ssl_certificates) > 0 and alb_config.is_enabled():
                cfn_export_dict['Certificates'] = []
                for ssl_cert_idx in range(0, len(listener.ssl_certificates)):
                    ssl_cert_param = self.create_cfn_parameter(
                        param_type='String',
                        name='SSLCertificateIdL%sC%d' % (listener_name, ssl_cert_idx),
                        description='The Arn of the SSL Certificate to associate with this Load Balancer',
                        value=listener.ssl_certificates[ssl_cert_idx] + ".arn",
                        use_troposphere=True,
                        troposphere_template=self.template
                    )
                    if ssl_cert_idx == 0:
                        cfn_export_dict['Certificates'] = [ {
                            'CertificateArn': troposphere.Ref(ssl_cert_param)
                        } ]
                    ssl_cert_param_obj_list.append(
                        troposphere.elasticloadbalancingv2.Certificate(
                            CertificateArn=troposphere.Ref(ssl_cert_param)
                        )
                    )


            listener_resource = troposphere.elasticloadbalancingv2.Listener.from_dict(
                logical_listener_name,
                cfn_export_dict
            )
            self.template.add_resource(listener_resource)

            # ListenerCertificates
            if len(ssl_cert_param_obj_list) > 0:
                troposphere.elasticloadbalancingv2.ListenerCertificate(
                    title=logical_listener_name+'Certificate',
                    template=self.template,
                    Certificates=ssl_cert_param_obj_list,
                    ListenerArn=troposphere.Ref(listener_resource)
                )

            # Listener - Rules
            if listener.rules != None:
                for rule_name, rule in listener.rules.items():
                    if rule.enabled == False:
                      continue
                    logical_rule_name = self.create_cfn_logical_id(rule_name)
                    cfn_export_dict = {}
                    if rule.rule_type == "forward":
                        cfn_export_dict['Actions'] = [
                            {'Type': 'forward', 'TargetGroupArn': troposphere.Ref('TargetGroup' + rule.target_group) }
                        ]
                    elif rule.rule_type == "redirect":
                        cfn_export_dict['Actions'] = [
                            {'Type': 'redirect', 'RedirectConfig': {'Host': rule.redirect_host, 'StatusCode': 'HTTP_301'} }
                        ]
                    cfn_export_dict['ListenerArn'] = troposphere.Ref(logical_listener_name)
                    cfn_export_dict['Conditions'] = [
                        {'Field': 'host-header', 'Values': [rule.host] }
                    ]
                    cfn_export_dict['Priority'] = rule.priority
                    logical_listener_rule_name = self.create_cfn_logical_id_join(
                        str_list=[logical_listener_name, 'Rule', logical_rule_name]
                    )
                    listener_rule_resource = troposphere.elasticloadbalancingv2.ListenerRule.from_dict(
                        logical_listener_rule_name,
                        cfn_export_dict
                    )
                    listener_rule_resource.Condition = "ALBIsEnabled"
                    self.template.add_resource(listener_rule_resource)

        # Record Sets
        if self.paco_ctx.legacy_flag('route53_record_set_2019_10_16'):
            record_set_index = 0
            for alb_dns in alb_config.dns:
                if alb_config.is_dns_enabled() == True:
                    hosted_zone_param = self.create_cfn_parameter(
                        param_type='String',
                        name='HostedZoneID%d' % (record_set_index),
                        value=alb_dns.hosted_zone+'.id',
                        use_troposphere=True,
                        troposphere_template=self.template
                    )
                    cfn_export_dict = {}
                    cfn_export_dict['HostedZoneId'] = troposphere.Ref(hosted_zone_param)
                    cfn_export_dict['Name'] = alb_dns.domain_name
                    cfn_export_dict['Type'] = 'A'
                    cfn_export_dict['AliasTarget'] = {
                        'DNSName': troposphere.GetAtt(alb_resource, 'DNSName'),
                        'HostedZoneId': troposphere.GetAtt(alb_resource, 'CanonicalHostedZoneID')
                    }
                    record_set_resource = troposphere.route53.RecordSet.from_dict(
                        'RecordSet' + record_set_index,
                        cfn_export_dict
                    )
                    record_set_resource.Condition = "ALBIsEnabled"
                    self.template.add_resource(record_set_resource)
                    record_set_index += 1

        if self.enabled == True:
            self.template.add_output(
                troposphere.Output(
                    title='LoadBalancerArn',
                    Value=troposphere.Ref(alb_resource)
                )
            )
            self.register_stack_output_config(alb_config.paco_ref_parts + '.arn', 'LoadBalancerArn')
            self.template.add_output(
                troposphere.Output(
                    title='LoadBalancerName',
                    Value=troposphere.GetAtt(alb_resource, 'LoadBalancerName')
                )
            )
            self.register_stack_output_config(alb_config.paco_ref_parts + '.name', 'LoadBalancerName')
            self.template.add_output(
                troposphere.Output(
                    title='LoadBalancerFullName',
                    Value=troposphere.GetAtt(alb_resource, 'LoadBalancerFullName')
                )
            )
            self.register_stack_output_config(alb_config.paco_ref_parts + '.fullname', 'LoadBalancerFullName')
            self.template.add_output(
                troposphere.Output(
                    title='LoadBalancerCanonicalHostedZoneID',
                    Value=troposphere.GetAtt(alb_resource, 'CanonicalHostedZoneID')
                )
            )

            self.register_stack_output_config(alb_config.paco_ref_parts + '.canonicalhostedzoneid', 'LoadBalancerCanonicalHostedZoneID')
            self.template.add_output(
                troposphere.Output(
                    title='LoadBalancerDNSName',
                    Value=troposphere.GetAtt(alb_resource, 'DNSName')
                )
            )
            self.register_stack_output_config(alb_config.paco_ref_parts + '.dnsname', 'LoadBalancerDNSName')

            if self.paco_ctx.legacy_flag('route53_record_set_2019_10_16') == False:
                route53_ctl = self.paco_ctx.get_controller('route53')
                for alb_dns in alb_config.dns:
                    if alb_config.is_dns_enabled() == True:
                        alias_dns_ref = alb_config.paco_ref + '.dnsname'
                        alias_hosted_zone_ref = alb_config.paco_ref + '.canonicalhostedzoneid'
                        hosted_zone = get_model_obj_from_ref(alb_dns.hosted_zone, self.paco_ctx.project)
                        account_ctx = self.paco_ctx.get_account_context(account_ref=hosted_zone.account)
                        route53_ctl.add_record_set(
                            account_ctx,
                            self.aws_region,
                            enabled=alb_config.is_enabled(),
                            dns=alb_dns,
                            record_set_type='Alias',
                            alias_dns_name=alias_dns_ref,
                            alias_hosted_zone_id=alias_hosted_zone_ref,
                            stack_group=self.stack_group,
                            config_ref=alb_config.paco_ref_parts + '.dns'
                        )

        self.set_template(self.template.to_yaml())

from paco import utils
from paco.cftemplates.cftemplates import StackTemplate
from paco.models import references
from paco.models.references import Reference
from paco.core.exception import StackException, PacoErrorCode
import troposphere


class SecurityGroups(StackTemplate):
    def __init__(
        self,
        stack,
        paco_ctx,
        env_ctx,
        template_type,
    ):
        security_groups_config = stack.resource
        sg_group_id = security_groups_config.name
        sg_groups_config_ref = security_groups_config.paco_ref_parts

        self.env_ctx = env_ctx
        super().__init__(
            stack,
            paco_ctx,
        )
        rules_id = None
        if template_type == 'Rules':
            rules_id = 'Rules'
        if self.paco_ctx.legacy_flag('cftemplate_aws_name_2019_09_17') == True:
            template_name = 'SecurityGroups'
        else:
            template_name = 'SG'
        self.set_aws_name(template_name, sg_group_id, rules_id)

        self.source_group_param_cache = {}

        # Troposphere Template Initialization
        self.init_template('Security Groups')
        template = self.template

        # VPC Id
        vpc_id_param = self.create_cfn_parameter(
            name='VPC',
            param_type='AWS::EC2::VPC::Id',
            description='The VPC Id',
            value='paco.ref netenv.{}.<environment>.<region>.network.vpc.id'.format(self.env_ctx.netenv.name),
        )

        # Security Group and Ingress/Egress Resources
        is_sg_enabled = False
        for sg_name in sorted(security_groups_config.keys()):
            sg_config = security_groups_config[sg_name]
            if sg_config.is_enabled():
                is_sg_enabled = True

            if template_type == 'Groups':
                self.create_group(sg_group_id, sg_name, sg_config, template, vpc_id_param)
            else:
                self.create_group_rules(sg_group_id, sg_name, sg_config, template)

        self.set_enabled(is_sg_enabled)

        self.set_template()
        if template_type == 'Rules':
            self.stack.wait_for_delete = True

    def create_group(self, sg_group_id, sg_name, sg_config, template, vpc_id_param):
        # GroupName
        group_name = self.create_resource_name_join(
            [ self.env_ctx.netenv.name, self.env_ctx.env.name, sg_group_id, sg_name ],
            separator='-',
            camel_case=True,
            filter_id='SecurityGroup.GroupName'
        )
        # GroupDescription
        if sg_config.group_description != None and sg_config.group_description != '':
            group_description = sg_config.group_description
        else:
            group_description = "Paco generated Security Group"
            # legacy_flag: aim_name_2019_11_28 - Use AIM name
            if self.paco_ctx.legacy_flag('aim_name_2019_11_28') == True:
                group_description = "AIM generated Security Group"

        # Security Group
        group_logical_id = self.create_cfn_logical_id(sg_name)
        group_res = troposphere.ec2.SecurityGroup(
            title = group_logical_id,
            template = template,
            GroupName = group_name,
            GroupDescription = group_description,
            VpcId = troposphere.Ref(vpc_id_param),
            Tags = troposphere.codebuild.Tags(
                Name = group_name
            )
        )

        # Output
        group_config_ref = '.'.join([self.config_ref, sg_name])
        self.create_output(
            title=group_logical_id + 'Id',
            value=troposphere.Ref(group_res),
            ref=group_config_ref + '.id'
        )

    def create_group_rules(self, sg_group_id, sg_name, sg_config, template):
        sg_group_config_ref = 'paco.ref ' + '.'.join([self.config_ref, sg_name])
        # Security Group Ingress and Egress rules
        for sg_rule_type in ['Ingress', 'Egress']:
            # Remove Ingress/Egress rules when disabled
            if sg_config.is_enabled() == False:
                break
            if sg_rule_type == 'Ingress':
                sg_rule_list = sg_config.ingress
                tropo_rule_method = troposphere.ec2.SecurityGroupIngress
            elif sg_rule_type == 'Egress':
                sg_rule_list = sg_config.egress
                tropo_rule_method = troposphere.ec2.SecurityGroupEgress
            else:
                raise StackException(PacoErrorCode.Unknown)

            # Ingress and Egress rules
            for sg_rule_config in sg_rule_list:
                rule_dict = {
                    'GroupId': self.create_group_param_ref(sg_group_config_ref, template),
                    'IpProtocol': str(sg_rule_config.protocol),
                    'FromPort': None,
                    'ToPort': None,
                    'Description': None
                }
                # Rule Name
                sg_rule_hash = sg_rule_config.obj_hash()[:8].upper()
                rule_name = self.create_cfn_logical_id(sg_name + sg_rule_hash + sg_rule_type + sg_rule_config.name)
                # FromPort and ToPort
                if sg_rule_config.port != -1:
                    rule_dict['FromPort'] = str(sg_rule_config.port)
                    rule_dict['ToPort'] = str(sg_rule_config.port)
                else:
                    rule_dict['FromPort'] = sg_rule_config.from_port
                    rule_dict['ToPort'] = sg_rule_config.to_port

                # Description
                if sg_rule_config.description != None and sg_rule_config.description != '':
                    rule_dict['Description'] = sg_rule_config.description
                else:
                    rule_dict['Description'] = 'unknown'

                # Source and Destination
                if sg_rule_config.cidr_ip != '':
                    rule_dict['CidrIp'] = sg_rule_config.cidr_ip
                elif sg_rule_config.cidr_ip_v6 != '':
                    rule_dict['CidrIpv6'] = sg_rule_config.cidr_ip_v6
                elif getattr(sg_rule_config, 'source_security_group', '') != '':
                    if references.is_ref(sg_rule_config.source_security_group):
                        rule_dict['SourceSecurityGroupId'] = self.create_group_param_ref(
                            sg_rule_config.source_security_group, template)
                    else:
                        rule_dict['SourceSecurityGroupId'] = sg_rule_config.source_security_group
                elif getattr(sg_rule_config, 'destination_security_group', '') != '':
                    if references.is_ref(sg_rule_config.destination_security_group):
                        rule_dict['DestinationSecurityGroupId'] = self.create_group_param_ref(
                            sg_rule_config.destination_security_group, template)
                    else:
                        rule_dict['DestinationSecurityGroupId'] = sg_rule_config.destination_security_group
                else:
                    raise StackException(PacoErrorCode.Unknown)

                # SecurityGroup Ingress/Egress
                rule_res = tropo_rule_method.from_dict(rule_name, rule_dict)
                template.add_resource(rule_res)


    def create_group_param_ref(self, group_ref, template):
        """
        Creates a Security Group Id parameter and returns a Ref()
        to it. It caches the parameter to allow multiple references
        from a single Parameter.
        """
        # legacy_flag: aim_name_2019_11_28 - hash with aim.ref instead of paco.ref
        hash_ref = group_ref
        if self.paco_ctx.legacy_flag('aim_name_2019_11_28') == True:
            hash_ref = 'aim' + group_ref[4:]
        group_ref_hash = utils.md5sum(str_data=hash_ref)
        if group_ref_hash in self.source_group_param_cache.keys():
            return troposphere.Ref(self.source_group_param_cache[group_ref_hash])

        source_sg_param = self.create_cfn_parameter(
            param_type='AWS::EC2::SecurityGroup::Id',
            name='SourceGroupId' + group_ref_hash,
            description='Source Security Group - ' + hash_ref,
            value=group_ref + '.id',
        )

        self.source_group_param_cache[group_ref_hash] = source_sg_param
        return troposphere.Ref(self.source_group_param_cache[group_ref_hash])



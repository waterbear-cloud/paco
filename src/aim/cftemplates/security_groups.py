import os
import troposphere
from aim import utils
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from aim.models import references
from aim.models.references import Reference
from aim.core.exception import StackException, AimErrorCode
from io import StringIO
from enum import Enum


class SecurityGroups(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 env_ctx,
                 security_groups_config,
                 sg_group_id,
                 sg_groups_config_ref):

        #aim_ctx.log("SecurityGroup CF Template init")

        self.env_ctx = env_ctx

        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=sg_groups_config_ref,
            aws_name='-'.join(["SecurityGroups", sg_group_id]),
            stack_group=stack_group,
            stack_tags=stack_tags
        )

        # Troposphere Template Initialization
        template = troposphere.Template()
        template.set_version('2010-09-09')
        template.set_description('Security Groups')

        template.add_resource(
            troposphere.cloudformation.WaitConditionHandle(title="DummyResource")
        )

        # VPC Id
        vpc_id_param = self.create_cfn_parameter(
            name='VPC',
            param_type='AWS::EC2::VPC::Id',
            description='The VPC Id',
            value='aim.ref netenv.{}.<account>.<region>.network.vpc.id'.format(self.env_ctx.netenv_id),
            use_troposphere=True
        )
        template.add_parameter(vpc_id_param)

        # Security Group and Ingress/Egress Resources
        is_sg_enabled = False
        for sg_name in sorted(security_groups_config.keys()):
            sg_config = security_groups_config[sg_name]
            if sg_config.is_enabled():
                is_sg_enabled = True

            # GroupName
            group_name = self.create_resource_name_join(
                [ self.env_ctx.netenv_id, self.env_ctx.env_id, sg_group_id, sg_name ],
                separator='-',
                camel_case=True,
                filter_id='SecurityGroup.GroupName'
            )
            # GroupDescription
            if sg_config.group_description != None and sg_config.group_description != '':
                group_description = sg_config.group_description
            else:
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

            group_output_logical_id = group_logical_id+'Id'
            group_output = troposphere.Output(
                title = group_output_logical_id,
                Value = troposphere.Ref(group_res)
            )
            template.add_output(group_output)

            group_config_ref = '.'.join([sg_groups_config_ref, sg_name])
            self.register_stack_output_config(group_config_ref+'.id', group_output_logical_id)

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
                    raise StackException(AimErrorCode.Unknown)

                # Ingress and Egress rules
                for sg_rule_config in sg_rule_list:
                    rule_dict = {
                        'GroupId': troposphere.Ref(group_res),
                        'IpProtocol': str(sg_rule_config.protocol),
                        'FromPort': None,
                        'ToPort': None,
                        'Description': None
                    }
                    # Rule Name
                    sg_rule_hash = utils.md5sum(str_data='{}'.format(sg_rule_config.__dict__))[:8].upper()
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

                    # Source
                    if sg_rule_config.cidr_ip != '':
                        rule_dict['CidrIp'] = sg_rule_config.cidr_ip
                    elif sg_rule_config.source_security_group != '':
                        # XXX: TODO: This only handles references to security groups within the
                        #            template currently being generated.
                        if references.is_ref(sg_rule_config.source_security_group):
                            source_sg = self.get_local_sg_ref(sg_rule_config.source_security_group+'.id')
                            rule_dict['SourceSecurityGroupId'] = troposphere.Ref(self.create_cfn_logical_id(source_sg))
                        else:
                            rule_dict['SourceSecurityGroupId'] = sg_rule_config.source_security_group
                    else:
                        raise StackException(AimErrorCode.Unknown)

                    # SecurityGroup Ingress/Egress
                    rule_res = tropo_rule_method.from_dict(rule_name, rule_dict)
                    template.add_resource(rule_res)

        self.enabled = is_sg_enabled
        self.set_template(template.to_yaml())

    def get_local_sg_ref(self, aim_ref):
        ref = Reference(aim_ref)
        return ref.parts[-2]


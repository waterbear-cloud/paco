from paco.cftemplates.cftemplates import StackTemplate
from paco.models.references import Reference
import json
import troposphere
import troposphere.elasticsearch


class ElasticsearchDomain(StackTemplate):
    def __init__(self, stack, paco_ctx):
        esdomain = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name('ESDomain', self.resource_group_name, self.resource_name)
        self.esdomain = esdomain
        self.init_template('Elasticsearch Domain')

        # if disabled then leave an empty placeholder and finish
        if not esdomain.is_enabled(): return

        # Parameters
        elasticsearch_version_param = self.create_cfn_parameter(
            name='ElasticsearchVersion',
            param_type='String',
            description='The version of Elasticsearch to use, such as 2.3.',
            value=self.esdomain.elasticsearch_version
        )
        subnet_params = []
        if esdomain.segment != None:
            segment_ref = esdomain.env_region_obj.network.vpc.segments[esdomain.segment].paco_ref
            if esdomain.cluster != None:
                if esdomain.cluster.zone_awareness_enabled:
                    azs = esdomain.cluster.zone_awareness_availability_zone_count
                else:
                    azs = 1
            else:
                azs = 2
            for az_idx in range(1, azs + 1):
                subnet_params.append(
                    self.create_cfn_parameter(
                        param_type='String',
                        name='ESDomainSubnet{}'.format(az_idx),
                        description='A subnet for the Elasticsearch Domain',
                        value='{}.az{}.subnet_id'.format(segment_ref, az_idx)
                    )
                )

        sg_params = []
        vpc_sg_list = []
        if esdomain.security_groups:
            for sg_ref in esdomain.security_groups:
                ref = Reference(sg_ref)
                sg_param_name = 'SecurityGroupId' + ref.parts[-2] + ref.parts[-1]
                sg_param = self.create_cfn_parameter(
                    name=sg_param_name,
                    param_type='String',
                    description='Security Group Id',
                    value=sg_ref + '.id',
                )
                sg_params.append(sg_param)
                vpc_sg_list.append(troposphere.Ref(sg_param))

        # ElasticsearchDomain resource
        esdomain_logical_id = 'ElasticsearchDomain'
        cfn_export_dict = esdomain.cfn_export_dict
        if esdomain.access_policies_json != None:
            cfn_export_dict['AccessPolicies'] = json.loads(esdomain.access_policies_json)

        # ToDo: VPC currently fails as there needs to be a service-linked role for es.amazonaws.com
        # to allow it to create the ENI
        if esdomain.segment != None:
            cfn_export_dict['VPCOptions'] = {'SubnetIds': [troposphere.Ref(param) for param in subnet_params] }
            if esdomain.security_groups:
                cfn_export_dict['VPCOptions']['SecurityGroupIds'] = vpc_sg_list

        esdomain_resource = troposphere.elasticsearch.ElasticsearchDomain.from_dict(
            esdomain_logical_id,
            cfn_export_dict,
        )
        self.template.add_resource(esdomain_resource)

        # Outputs
        self.create_output(
            title='Name',
            value=troposphere.Ref(esdomain_resource),
            description='ElasticsearchDomain name',
            ref=esdomain.paco_ref_parts + '.name',
        )
        self.create_output(
            title='Arn',
            description='Arn of the domain. The same value as DomainArn.',
            value=troposphere.GetAtt(esdomain_resource, 'Arn'),
            ref=esdomain.paco_ref_parts  + '.arn',
        )
        self.create_output(
            title='DomainArn',
            description='DomainArn of the domain. The same value as Arn.',
            value=troposphere.GetAtt(esdomain_resource, "DomainArn"),
            ref=esdomain.paco_ref_parts + '.domainarn',
        )
        self.create_output(
            title='DomainEndpoint',
            description="The domain-specific endpoint that's used to submit index, search, and data upload requests to an Amazon ES domain.",
            value=troposphere.GetAtt(esdomain_resource, 'DomainEndpoint'),
            ref=esdomain.paco_ref_parts + '.domainendpoint',
        )

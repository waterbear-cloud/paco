"""
CloudFormation templates for API Gateway
"""

import awacs.sts
import awacs.awslambda
import troposphere
import troposphere.apigateway
import troposphere.iam
from aim.cftemplates.cftemplates import CFTemplate
from aim.models import references
from aim.models.references import Reference
from awacs.aws import Allow, Statement, Policy, Principal


class ApiGatewayRestApi(CFTemplate):
    """
    CloudFormation template for ApiGatewayRestApi
    """
    def __init__(
        self,
        aim_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        aws_name,
        app_id,
        grp_id,
        apigatewayrestapi,
        config_ref=None,
    ):
        aws_name='-'.join([aws_name, 'ApiGatewayRestApi'])
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=config_ref,
            aws_name=aws_name,
            stack_group=stack_group,
            stack_tags=stack_tags,
            iam_capabilities=["CAPABILITY_IAM"],
        )
        self.apigatewayrestapi = apigatewayrestapi

        # ---------------------------------------------------------------------------
        # Troposphere Template Initialization

        template = troposphere.Template()
        template.add_version('2010-09-09')
        template.add_description(apigatewayrestapi.title)


        # ---------------------------------------------------------------------------
        # Parameters

        method_params = []
        for method in self.apigatewayrestapi.methods.values():
            param_name = 'MethodArn' + self.create_cfn_logical_id(method.name)
            lambda_arn_param = self.create_cfn_parameter(
                name=param_name,
                param_type='String',
                description='Lambda ARN parameter.',
                value=method.integration_lambda,
                use_troposphere=True
            )
            method.parameter_arn_ref = troposphere.Ref(param_name)
            template.add_parameter(lambda_arn_param)

        # ---------------------------------------------------------------------------
        # Resources

        restapi_logical_id = 'ApiGatewayRestApi'
        restapi_resource = troposphere.apigateway.RestApi.from_dict(
            restapi_logical_id,
            self.apigatewayrestapi.cfn_export_dict
        )
        template.add_resource(restapi_resource)

        # Resource
        for resource in self.apigatewayrestapi.resources.values():
            resource_id = 'ApiGatewayResource' + self.create_cfn_logical_id(resource.name)
            cfn_export_dict = resource.cfn_export_dict
            if resource.parent_id == "RootResourceId":
                cfn_export_dict["ParentId"] = troposphere.GetAtt(restapi_resource, "RootResourceId")
                cfn_export_dict["RestApiId"] = troposphere.Ref(restapi_resource)
            else:
                raise NotImplemented("ToDo: handle nested resources")
            resource_resource = troposphere.apigateway.Resource.from_dict(resource_id, cfn_export_dict)
            resource.resource = resource_resource
            resource_resource.DependsOn = restapi_logical_id
            template.add_resource(resource_resource)

        # Method
        for method in self.apigatewayrestapi.methods.values():
            method_id = 'ApiGatewayMethod' + self.create_cfn_logical_id(method.name)
            method.logical_id = method_id
            cfn_export_dict = method.cfn_export_dict
            for resource in self.apigatewayrestapi.resources.values():
                if resource.name == method.resource_id:
                    cfn_export_dict["ResourceId"] = troposphere.Ref(resource.resource)
            cfn_export_dict["RestApiId"] = troposphere.Ref(restapi_resource)
            uri = troposphere.Join('', ["arn:aws:apigateway:", method.region_name, ":lambda:path/2015-03-31/functions/", method.parameter_arn_ref, "/invocations"])
            cfn_export_dict["Integration"]["Uri"] = uri

            # IAM Role - allows API Gateway to invoke Lambda
            # ToDo: enable Api Gateway to invoke things other than Lambda ...
            iam_role_resource = troposphere.iam.Role(
                self.create_cfn_logical_id('ApiGatewayIamRole' + self.apigatewayrestapi.name + method.name),
                Path='/',
                AssumeRolePolicyDocument=Policy(
                    Version='2012-10-17',
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[awacs.sts.AssumeRole],
                            Principal=Principal('Service',['apigateway.amazonaws.com'])
                        )
                    ],
                ),
                Policies=[
                    troposphere.iam.Policy(
                        PolicyName=self.create_cfn_logical_id('LambdaAccessApiGateway' + self.apigatewayrestapi.name + method.name),
                        PolicyDocument=Policy(
                            Version='2012-10-17',
                            Statement=[
                                Statement(
                                    Effect=Allow,
                                    Action=[awacs.awslambda.InvokeFunction],
                                    Resource=[method.parameter_arn_ref],
                                )
                            ]
                        )
                    )
                ]
            )
            template.add_resource(iam_role_resource)

            # if this is value is not supplied, give method ability to assume ApiGateway role
            if not cfn_export_dict["Integration"]["Credentials"]:
                cfn_export_dict["Integration"]["Credentials"] = troposphere.GetAtt(iam_role_resource, "Arn")

            method_resource = troposphere.apigateway.Method.from_dict(method_id, cfn_export_dict)
            method_resource.DependsOn = restapi_logical_id
            template.add_resource(method_resource)

        # Model
        model = troposphere.apigateway.Model.from_dict(
            'ApiGatewayModel',
            {'Schema': {},
            'RestApiId': troposphere.Ref(restapi_resource)
            }
        )

        # Deployment
        deployment_resource = troposphere.apigateway.Deployment.from_dict(
            'ApiGatewayDeployment',
            {'Description': 'Deployment',
             'RestApiId': troposphere.Ref(restapi_resource) }
        )
        # ToDo: Deployment depends upon all Methods
        for method in self.apigatewayrestapi.methods.values():
            deployment_resource.DependsOn = method.logical_id
        template.add_resource(deployment_resource)

        # Stage
        for stage in self.apigatewayrestapi.stages.values():
            stage_id = self.create_cfn_logical_id('ApiGatewayStage' + stage.name)
            cfn_export_dict = stage.cfn_export_dict
            cfn_export_dict["RestApiId"] = troposphere.Ref(restapi_resource)
            cfn_export_dict["DeploymentId"] = troposphere.Ref(deployment_resource)
            stage_resource = troposphere.apigateway.Stage.from_dict(stage_id, cfn_export_dict)
            template.add_resource(stage_resource)

        # Generate the Template
        self.set_template(template.to_yaml())
"""
CloudFormation template for API Gateway
"""

from importlib import resources
from awacs.aws import Allow, Statement, Policy, Principal
from paco.models import schemas
from paco.models.resources import ApiGatewayMethod
from paco.models.loader import apply_attributes_from_config
from paco.models.schemas import get_parent_by_interface
from paco.cftemplates.cftemplates import StackTemplate
from paco.models.references import get_model_obj_from_ref
from paco.utils import md5sum
import awacs.sts
import awacs.awslambda
import troposphere
import troposphere.apigateway
import troposphere.awslambda
import troposphere.iam


class ApiGatewayRestApi(StackTemplate):
    """
    CloudFormation template for ApiGatewayRestApi
    """
    def __init__(self, stack, paco_ctx):
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_IAM"])
        self.apigatewayrestapi = apigatewayrestapi = stack.resource
        self.set_aws_name('ApiGatewayRestApi', self.resource_group_name, self.resource.name)

        self.init_template('ApiGateway: {}'.format(apigatewayrestapi.title))
        template = self.template
        if not self.apigatewayrestapi.is_enabled():
            return

        # Parameters
        lambda_params = {}
        for method in self.apigatewayrestapi.methods.values():
            if method.integration.integration_lambda != None:
                param_name = 'MethodArn' + self.create_cfn_logical_id(method.name)
                if method.integration.integration_lambda not in lambda_params:
                    lambda_params[method.integration.integration_lambda] = self.create_cfn_parameter(
                        name=param_name,
                        param_type='String',
                        description='Lambda ARN parameter.',
                        value=method.integration.integration_lambda + '.arn',
                    )
                method.parameter_arn_ref = troposphere.Ref(lambda_params[method.integration.integration_lambda])

        # Resources
        restapi_logical_id = 'ApiGatewayRestApi'
        cfn_export_dict = self.apigatewayrestapi.cfn_export_dict
        if self.paco_ctx.legacy_flag('aim_name_2019_11_28') == True:
            cfn_export_dict['Name'] = self.apigatewayrestapi.name

        self.restapi_resource = troposphere.apigateway.RestApi.from_dict(
            restapi_logical_id,
            cfn_export_dict
        )
        template.add_resource(self.restapi_resource)
        self.create_output(
            title='ApiGatewayRestApiId',
            value=troposphere.Ref(self.restapi_resource),
            ref=self.apigatewayrestapi.paco_ref_parts + '.id',
        )
        self.create_output(
            title='ApiGatewayRestApiAddress',
            value=troposphere.Join('.', [
                troposphere.Ref(self.restapi_resource),
                'execute-api',
                self.stack.aws_region,
                'amazonaws.com',
            ]),
            ref=self.apigatewayrestapi.paco_ref_parts + '.address',
        )
        self.create_output(
            title='ApiGatewayRestApiRootResourceId',
            value=troposphere.GetAtt(self.restapi_resource, "RootResourceId"),
            ref=self.apigatewayrestapi.paco_ref_parts + '.root_resource_id',
        )

        # Authorizers
        if self.apigatewayrestapi.cognito_authorizers != None:
            # monkey patch for Troposphere ... ToDo: file a PR
            troposphere.apigateway.Authorizer.props['AuthorizerUri'] = (str, False)
            self.user_pool_params = {}
            for cog_auth in self.apigatewayrestapi.cognito_authorizers.values():
                provider_arns = []
                for user_pool_ref in cog_auth.user_pools:
                    if user_pool_ref not in self.user_pool_params:
                        self.user_pool_params[user_pool_ref] = self.create_cfn_parameter(
                        name='CognitoUserPool' + md5sum(str_data=user_pool_ref),
                        param_type='String',
                        description='Cognito User Pool ARN',
                        value=user_pool_ref + '.arn',
                    )
                    provider_arns.append(troposphere.Ref(self.user_pool_params[user_pool_ref]))
                cog_auth_resource = troposphere.apigateway.Authorizer(
                    title=self.create_cfn_logical_id(f'CognitoAuthorizer{cog_auth.name}'),
                    Name=cog_auth.name,
                    RestApiId=troposphere.Ref(self.restapi_resource),
                    IdentitySource='method.request.header.' + cog_auth.identity_source,
                    Type='COGNITO_USER_POOLS',
                    ProviderARNs=provider_arns,
                )
                self.template.add_resource(cog_auth_resource)
                cog_auth.resource = cog_auth_resource

        # Model
        for model in self.apigatewayrestapi.models.values():
            model.logical_id = self.create_cfn_logical_id('ApiGatewayModel' + model.name)
            cfn_export_dict = model.cfn_export_dict
            cfn_export_dict['RestApiId'] = troposphere.Ref(self.restapi_resource)
            if 'Schema' not in cfn_export_dict:
                cfn_export_dict['Schema'] = {}
            model_resource = troposphere.apigateway.Model.from_dict(model.logical_id, cfn_export_dict)
            model.resource = model_resource
            template.add_resource(model_resource)

        # Resource
        self.recursively_add_resources(self.apigatewayrestapi.resources)

        # Method
        api_account_name = self.apigatewayrestapi.get_account().name
        for method in self.apigatewayrestapi.methods.values():
            method_depends_on = [ restapi_logical_id ]
            method_id = 'ApiGatewayMethod' + self.create_cfn_logical_id(method.name)
            method.logical_id = method_id
            cfn_export_dict = method.cfn_export_dict
            if method.authorizer != None:
                # ToDo: only Cognito Authorizers
                auth_type, auth_name = method.authorizer.split('.')
                auth_cont = getattr(self.apigatewayrestapi, auth_type)
                auth_obj = auth_cont[auth_name]
                cfn_export_dict["AuthorizerId"] = troposphere.Ref(auth_obj.resource)
                if auth_type == 'cognito_authorizers':
                    cfn_export_dict["AuthorizationType"] = 'COGNITO_USER_POOLS'
            if method.resource_name:
                cfn_export_dict["ResourceId"] = troposphere.Ref(method.get_resource().resource)
                method_depends_on.append(method.get_resource().resource)
            else:
                cfn_export_dict["ResourceId"] = troposphere.GetAtt(self.restapi_resource, 'RootResourceId')
            cfn_export_dict["RestApiId"] = troposphere.Ref(self.restapi_resource)

            # Lambad Integration
            if method.integration.integration_lambda != None:
                awslambda = get_model_obj_from_ref(method.integration.integration_lambda, self.project)
                uri = troposphere.Join('', [
                    "arn:aws:apigateway:",
                    awslambda.region_name,
                    ":lambda:path/2015-03-31/functions/",
                    method.parameter_arn_ref,
                    "/invocations"]
                )
                cfn_export_dict["Integration"]["Uri"] = uri

                if method.integration.integration_type == 'AWS_PROXY':
                    # Cross-account Lambda can not have a Role or gets a permission error
                    if api_account_name == awslambda.get_account().name:
                        # IAM Role - allows API Gateway to invoke Lambda
                        # ToDo: enable Api Gateway to invoke things other than Lambda ...
                        # ToDo: share Roles between methods!
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
                        cfn_export_dict["Integration"]["Credentials"] = troposphere.GetAtt(iam_role_resource, "Arn")

            elif method.integration.integration_type == 'AWS':
                # Enable Lambda (custom) integration
                # When send to a Lambda (Custom) the HTTP Method must always be POST regardless of
                # the HttpMethod
                cfn_export_dict["Integration"]["IntegrationHttpMethod"] = "POST"
                lambda_permission_resource = troposphere.awslambda.Permission(
                    self.create_cfn_logical_id('LambdaPermissionApiGateway' + method.name),
                    Action = 'lambda:InvokeFunction',
                    FunctionName = method.parameter_arn_ref,
                    Principal = 'apigateway.amazonaws.com',
                    SourceArn = troposphere.Sub(
                        "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${%s}/*/%s/" % (
                            restapi_logical_id, method.http_method
                        )
                    )
                )
                template.add_resource(lambda_permission_resource)

            # look-up the method_names and assign a Ref to the model resource
            # ToDo: validate model_names in the model
            responses = []
            for method_response in method.method_responses:
                response_dict = {"StatusCode": method_response.status_code}
                if method_response.response_models:
                    response_dict["ResponseModels"] = {}
                    for response_model in method_response.response_models:
                        for model in self.apigatewayrestapi.models.values():
                            if model.name == response_model.model_name:
                                response_dict["ResponseModels"][response_model.content_type] = troposphere.Ref(model.resource)
                if method_response.response_parameters:
                    response_dict["ResponseParameters"] = method_response.response_parameters
                responses.append(response_dict)
            cfn_export_dict["MethodResponses"] = responses

            method_resource = troposphere.apigateway.Method.from_dict(method_id, cfn_export_dict)
            method_resource.DependsOn = method_depends_on
            template.add_resource(method_resource)
            self.create_output(
                title=self.create_cfn_logical_id(f'ApiGatewayRestApiMethod{method.name}'),
                value=troposphere.Ref(method_resource),
                ref=method.paco_ref_parts + '.id',
            )

        # Deployment
        deployment_resource = troposphere.apigateway.Deployment.from_dict(
            'ApiGatewayDeployment',
            {'Description': 'Deployment',
             'RestApiId': troposphere.Ref(self.restapi_resource) }
        )
        # this is needed otherwise you can get 'No integration defined for method'
        # as the Deployment can be created before the Methods
        deployment_resource.DependsOn = [
            method.logical_id for method in self.apigatewayrestapi.methods.values()
        ]

        template.add_resource(deployment_resource)
        self.create_output(
            title=self.create_cfn_logical_id(f'ApiGatewayRestApiDeployment'),
            value=troposphere.Ref(deployment_resource),
            ref=self.apigatewayrestapi.paco_ref_parts + '.deploymnt_id',
        )

        # Stage
        self.stage_resources = []
        for stage in self.apigatewayrestapi.stages.values():
            stage_id = self.create_cfn_logical_id('ApiGatewayStage' + stage.name)
            cfn_export_dict = stage.cfn_export_dict
            cfn_export_dict["RestApiId"] = troposphere.Ref(self.restapi_resource)
            cfn_export_dict["DeploymentId"] = troposphere.Ref(deployment_resource)
            stage_resource = troposphere.apigateway.Stage.from_dict(stage_id, cfn_export_dict)
            self.stage_resources.append(stage_resource)
            template.add_resource(stage_resource)
            self.create_output(
                title=self.create_cfn_logical_id(f'ApiGatewayRestApiStage{stage.name}'),
                value=troposphere.Ref(stage_resource),
                ref=stage.paco_ref_parts + '.id',
            )

        # DNS
        # Caution: experimental code: REGIONAL endpoints only and
        # the dns.ssl_certificate field expects an Arn instead of a paco.ref to an ACM resource ...
        if self.apigatewayrestapi.is_dns_enabled() == True:
            route53_ctl = self.paco_ctx.get_controller('route53')
            for dns in self.apigatewayrestapi.dns:
                # ApiGateway DomainName resource
                domain_name_logical_id = self.create_cfn_logical_id('DomainName' + dns.domain_name)
                # ToDo: currently SSL Certificate must be an Arn
                # A paco.ref to an SSL Cert is typically in a netenv, which isn't initialized in a Service
                # either init the netenv or have some way of managing ACM certs globally?
                cfn_export_dict = {
                    'DomainName': dns.domain_name,
                    'RegionalCertificateArn': dns.ssl_certificate,
                    'EndpointConfiguration': {"Types": ['REGIONAL']},
                }
                domain_name_resource = troposphere.apigateway.DomainName.from_dict(
                    domain_name_logical_id,
                    cfn_export_dict
                )
                template.add_resource(domain_name_resource)
                domain_name_name = dns.domain_name.replace('.', '')
                self.create_output(
                    title=domain_name_logical_id,
                    value=troposphere.GetAtt(domain_name_resource, 'RegionalDomainName'),
                    ref=f'{dns.paco_ref_parts}.{domain_name_name}.regional_domain_name',
                )

                # ApiGateway BasePathMapping
                for base_path_mapping in dns.base_path_mappings:
                    cfn_export_dict = {
                        'DomainName': dns.domain_name,
                        'RestApiId': troposphere.Ref(self.restapi_resource),
                        'Stage': base_path_mapping.stage,
                    }
                    if base_path_mapping.base_path != '':
                        cfn_export_dict['BasePath'] = base_path_mapping.base_path
                    base_path_mapping_logical_id = self.create_cfn_logical_id('BasePathMapping' + dns.domain_name)
                    base_path_mapping_resource = troposphere.apigateway.BasePathMapping.from_dict(
                        base_path_mapping_logical_id,
                        cfn_export_dict,
                    )
                    base_path_mapping_resource.DependsOn = [domain_name_logical_id]
                    for stage in self.stage_resources:
                        base_path_mapping_resource.DependsOn.append(stage.title)
                    template.add_resource(base_path_mapping_resource)

                # CNAME for DomainName
                # ToDo: this fails if the ApiGateway DomainName resource isn't created first - make in the reseng?
                # route53_ctl.add_record_set(
                #     self.account_ctx,
                #     self.aws_region,
                #     self.apigatewayrestapi,
                #     enabled=self.apigatewayrestapi.is_enabled(),
                #     dns=dns,
                #     record_set_type='CNAME',
                #     resource_records=[f'{dns.paco_ref}.{domain_name_name}.regional_domain_name'],
                #     stack_group=self.stack.stack_group,
                #     async_stack_provision=False,
                # )

    def recursively_add_resources(self, resources_container):
        for resource in resources_container.values():
            self.add_apigateway_resource(resource)
            if len(resource.child_resources.keys()) > 0:
                self.recursively_add_resources(resource.child_resources)

    def add_apigateway_resource(self, resource):
        resource_logical_id = 'ApiGatewayResource' + self.create_cfn_logical_id(resource.name + md5sum(str_data=resource.paco_ref_parts))
        cfn_export_dict = resource.cfn_export_dict
        parent_resource = resource.__parent__.__parent__
        # root resource
        if schemas.IApiGatewayRestApi.providedBy(parent_resource):
            cfn_export_dict["ParentId"] = troposphere.GetAtt(self.restapi_resource, "RootResourceId")
        # child resource
        else:
            cfn_export_dict["ParentId"] = troposphere.Ref(parent_resource.resource)
        cfn_export_dict["RestApiId"] = troposphere.Ref(self.restapi_resource)
        resource_resource = troposphere.apigateway.Resource.from_dict(resource_logical_id, cfn_export_dict)
        resource.resource = resource_resource
        self.template.add_resource(resource_resource)
        self.create_output(
            title=self.create_cfn_logical_id(f'ApiGatewayRestApiResource{resource.name}' + md5sum(str_data=resource.paco_ref_parts)),
            value=troposphere.Ref(resource_resource),
            ref=resource.paco_ref_parts + '.id',
        )
        # Add an OPTIONS method if CORS is enabled
        if resource.enable_cors == True:
            options_config = {
                'http_method': 'OPTIONS',
                'integration': {
                    'integration_type': 'MOCK',
                    'integration_http_method': 'OPTIONS',
                    'pass_through_behavior': 'WHEN_NO_MATCH',
                    'request_templates': {'application/json': '{"statusCode": 200}'},
                    'integration_responses': [{
                        'status_code': '200',
                        'response_parameters': {
                            'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                            'method.response.header.Access-Control-Allow-Methods': "'POST,OPTIONS'",
                            'method.response.header.Access-Control-Allow-Origin': "'*'",
                        },
                        'response_templates': {'application/json': ''},
                    },],
                },
                'method_responses': [{
                    'status_code': '200',
                    'response_models': [{
                        'content_type': 'application/json',
                        'model_name': 'emptyjson',
                    }],
                    'response_parameters': {
                        'method.response.header.Access-Control-Allow-Headers': False,
                        'method.response.header.Access-Control-Allow-Methods': False,
                        'method.response.header.Access-Control-Allow-Origin': False,
                    },
                }],
            }
            options_config['resource_name'] = resource.nested_name
            method_name = f'{resource.nested_name}PacoCORS'
            options_method = ApiGatewayMethod(method_name, self.apigatewayrestapi.methods)
            apply_attributes_from_config(options_method, options_config)
            self.apigatewayrestapi.methods[method_name] = options_method

        return resource_resource

class ApiGatewayLamdaPermissions(StackTemplate):
    def __init__(self, stack, paco_ctx, awslambda):
        super().__init__(stack, paco_ctx)
        self.set_aws_name('ApiGatewayLamdaPermission', self.resource_group_name, self.resource_name)
        self.init_template('Cross-account Api Gateway Lambda Permission')
        apigateway = self.resource

        api_gateway_id_param = self.create_cfn_parameter(
            name=self.create_cfn_logical_id('ApiGatewayRestApiId'),
            param_type='String',
            description='API Gateway Rest API Id',
            value=apigateway.paco_ref + '.id',
        )
        lambda_arn_param = self.create_cfn_parameter(
            name=self.create_cfn_logical_id('LambdaArn'),
            param_type='String',
            description='Lambda Arn',
            value=awslambda.paco_ref + '.arn',
        )

        # Lambda Permission for cross-account API Gateway invocation
        for method in apigateway.methods.values():
            if method.integration != None and method.integration.integration_lambda != None:
                if awslambda.paco_ref == method.integration.integration_lambda:
                    if apigateway.get_account().name != awslambda.get_account().name:
                        # Grant Cross-Account API Gateway permission
                        path_part = ''
                        if method.resource_name:
                            name_parts = method.resource_name.split('.')
                            resource = method.get_resource()
                            if len(name_parts) > 1:
                                # child resource
                                last_resource = resource
                                while schemas.IApiGatewayResource.providedBy(resource):
                                    last_resource = resource
                                    resource = resource.__parent__.__parent__
                                path_part = last_resource.path_part + '/*' # add /* to match all child resource
                            else:
                                # parent resource
                                path_part = resource.path_part
                        lambda_permission_resource = troposphere.awslambda.Permission(
                            title='ApiGatewayRestApiMethod' + md5sum(str_data=method.paco_ref),
                            Action="lambda:InvokeFunction",
                            FunctionName=troposphere.Ref(lambda_arn_param),
                            Principal='apigateway.amazonaws.com',
                            SourceArn=troposphere.Join('', [
                                "arn:aws:execute-api:",
                                awslambda.region_name, # lambda region
                                ":",
                                apigateway.get_account().account_id, # account id
                                ":",
                                troposphere.Ref(api_gateway_id_param),
                                f"/*/{method.http_method}/{path_part}",
                            ])
                        )
                        self.template.add_resource(lambda_permission_resource)

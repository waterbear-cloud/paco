from awacs.aws import PolicyDocument, Principal, Statement, Allow, Action, Condition, ForAnyValueStringLike, Policy
from awacs.aws import StringEquals
from paco.models.references import Reference
from paco.models.schemas import ICognitoUserPool, get_parent_by_interface
from paco.cftemplates.cftemplates import StackTemplate
from paco.cftemplates.iam_roles import role_to_troposphere
from paco.stack import StackHooks
from paco.utils import md5sum
import awacs.sns
import troposphere.cognito
import troposphere.iam
import troposphere.awslambda


class CognitoUserPool(StackTemplate):
    def __init__(self, stack, paco_ctx):
        cup = stack.resource
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_IAM"])
        self.set_aws_name('CUP', self.resource_group_name, self.resource.name)

        self.init_template('Cognito User Pool')
        if not cup.is_enabled():
            return

        cfn_export_dict = cup.cfn_export_dict

        # SNS Role for SMS
        if cup.mfa != 'off':
            # CloudFormation requires an SMS Role even if only software tokens are used
            sms_role_resource = troposphere.iam.Role(
                'CognitoSMSRole',
                AssumeRolePolicyDocument=PolicyDocument(
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Principal=Principal('Service',"cognito-idp.amazonaws.com"),
                            Action=[Action('sts', 'AssumeRole')],
                            Condition=Condition([
                                StringEquals({"sts:ExternalId": cup.paco_ref_parts}),
                            ]),
                        ),
                    ],
                ),
                Policies=[
                    troposphere.iam.Policy(
                        PolicyName="AllowSMS",
                        PolicyDocument=Policy(
                            Version='2012-10-17',
                            Statement=[
                                Statement(
                                    Effect=Allow,
                                    Action=[awacs.sns.Publish],
                                    Resource=['*'],
                                )
                            ]
                        )
                    )
                ],
            )
            self.template.add_resource(sms_role_resource)
            cfn_export_dict['SmsConfiguration'] = {
                'ExternalId': cup.paco_ref_parts,
                'SnsCallerArn': troposphere.GetAtt(sms_role_resource, "Arn")
            }

        # Lambda Triggers
        lambda_trigger_mapping = [
            ('create_auth_challenge', 'CreateAuthChallenge'),
            ('custom_message', 'CustomMessage'),
            ('define_auth_challenge', 'DefineAuthChallenge'),
            ('post_authentication', 'PostAuthentication'),
            ('post_confirmation', 'PostConfirmation'),
            ('pre_authentication', 'PreAuthentication'),
            ('pre_sign_up', 'PreSignUp'),
            ('pre_token_generation', 'PreTokenGeneration'),
            ('user_migration', 'UserMigration'),
            ('verify_auth_challenge_response', 'VerifyAuthChallengeResponse'),
        ]
        self.lambda_trigger_params = {}
        if cup.lambda_triggers != None:
            triggers = {}
            for name, cfn_key in lambda_trigger_mapping:
                lambda_ref = getattr(cup.lambda_triggers, name, None)
                if lambda_ref != None:
                    if lambda_ref not in self.lambda_trigger_params:
                        self.lambda_trigger_params[lambda_ref] = self.create_cfn_parameter(
                            param_type='String',
                            name='LambdaTrigger' + md5sum(str_data=lambda_ref),
                            description=f'LambdaTrigger for Lambda {lambda_ref}',
                            value=lambda_ref + '.arn',
                        )
                    triggers[cfn_key] = troposphere.Ref(self.lambda_trigger_params[lambda_ref])
            cfn_export_dict['LambdaConfig'] = triggers

        # Cognito User Pool
        cup_resource = troposphere.cognito.UserPool.from_dict(
            'CognitoUserPool',
            cfn_export_dict
        )
        self.template.add_resource(cup_resource)

        # Add Lambda Permissions for Lambda Triggers
        # Need to do this after the cup_resource is created
        lambda_permissions = {}
        if cup.lambda_triggers != None:
            for name, cfn_key in lambda_trigger_mapping:
                lambda_ref = getattr(cup.lambda_triggers, name, None)
                if lambda_ref != None:
                    # Lambda Permission
                    if lambda_ref not in lambda_permissions:
                        lambda_permissions[lambda_ref] = True
                        troposphere.awslambda.Permission(
                            title='LambdaPermission' + md5sum(str_data=cup.paco_ref_parts),
                            template=self.template,
                            Action="lambda:InvokeFunction",
                            FunctionName=troposphere.Ref(self.lambda_trigger_params[lambda_ref]),
                            Principal='cognito-idp.amazonaws.com',
                            SourceArn=troposphere.GetAtt(cup_resource, "Arn"),
                        )

        # Outputs
        self.create_output(
            title=cup_resource.title + 'Id',
            description="Cognito UserPool Id",
            value=troposphere.Ref(cup_resource),
            ref=[cup.paco_ref_parts, cup.paco_ref_parts + ".id"],
        )
        self.create_output(
            title=cup_resource.title + 'Arn',
            description="Cognito UserPool Arn",
            value=troposphere.GetAtt(cup_resource, "Arn"),
            ref=cup.paco_ref_parts + ".arn"
        )
        self.create_output(
            title=cup_resource.title + 'ProviderName',
            description="Cognito UserPool ProviderName",
            value=troposphere.GetAtt(cup_resource, "ProviderName"),
            ref=[cup.paco_ref_parts + ".name", cup.paco_ref_parts + ".providername"],
        )
        self.create_output(
            title=cup_resource.title + 'Url',
            description="Cognito UserPool ProviderURL",
            value=troposphere.GetAtt(cup_resource, "ProviderURL"),
            ref=[cup.paco_ref_parts + ".url", cup.paco_ref_parts + ".providerurl"],
        )

        # Cognito User Pool Clients
        for client in cup.app_clients.values():
            cfn_export_dict = client.cfn_export_dict
            cfn_export_dict['UserPoolId'] = troposphere.Ref(cup_resource)
            client_logical_id = self.create_cfn_logical_id(f"{client.name}CognitoUserPoolClient")
            cupclient_resource = troposphere.cognito.UserPoolClient.from_dict(
                client_logical_id,
                cfn_export_dict
            )
            self.template.add_resource(cupclient_resource)
            self.create_output(
                title=cupclient_resource.title + 'Id',
                description="Cognito UserPoolClient Id",
                value=troposphere.Ref(cupclient_resource),
                ref=client.paco_ref_parts + ".id",
            )
            if client.domain_name:
                # ToDo: add support for custom domains
                up_domain_name = self.create_cfn_logical_id(f"{client.name}UserPoolDomain")
                domain_resource = troposphere.cognito.UserPoolDomain(
                    up_domain_name,
                    Domain=client.domain_name,
                    UserPoolId=troposphere.Ref(cup_resource)
                )
                self.template.add_resource(domain_resource)

        # UI Customizations
        if cup.ui_customizations != None:
            if cup.ui_customizations.logo_file != None or cup.ui_customizations.css_file != None:
                # Add a Hook to set UI Customizations
                # CloudFormation doesn't support the Logo customization
                # Paco also uses the hook for CSS (this could be migration to the CloudFormation ~shrug~)
                stack_hooks = StackHooks()
                stack_hooks.add(
                    name='SetCognitoUICustomizations',
                    stack_action=['create','update'],
                    stack_timing='post',
                    hook_method=self.add_ui_customizations_hook,
                    cache_method=self.add_ui_customizations_cache,
                    hook_arg=cup,
                )
                stack.add_hooks(stack_hooks)

    def add_ui_customizations_cache(self, hook, cup):
        value = ''
        if cup.ui_customizations.logo_file != None:
            value += md5sum(bytes_data=cup.ui_customizations.logo_file)
        if cup.ui_customizations.css_file != None:
            value += md5sum(str_data=cup.ui_customizations.css_file)
        return value

    def add_ui_customizations_hook(self, hook, cup):
        cup_id = cup.stack.get_output_value_by_ref_extension('id')
        # ToDo: add support for per app_client customizations
        # app_client_id = cup.stack.get_output_value_by_ref_extension('app_clients.<xxx≥.id')
        # ClientId=app_client_id,
        client = self.account_ctx.get_aws_client('cognito-idp', self.aws_region)
        args_dict = {
            'UserPoolId': cup_id,
        }
        if cup.ui_customizations.css_file != None:
            args_dict['CSS'] = cup.ui_customizations.css_file
        if cup.ui_customizations.css_file != None:
            args_dict['ImageFile'] = cup.ui_customizations.logo_file
        client.set_ui_customization(**args_dict)


class CognitoIdentityPool(StackTemplate):
    def __init__(self, stack, paco_ctx):
        cip = stack.resource
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_IAM"])
        self.set_aws_name('CIP', self.resource_group_name, self.resource.name)

        self.init_template('Cognito Identity Pool')
        if not cip.is_enabled():
            return

        # Cognito Identity Pool
        cfn_export_dict = cip.cfn_export_dict
        if len(cip.identity_providers) > 0:
            idps = []
            up_client_params = {}
            up_params = {}
            for idp in cip.identity_providers:
                # replace <region> and <account> for refs in Services
                up_client_ref = Reference(idp.userpool_client)
                up_client_ref.set_account_name(self.account_ctx.get_name())
                up_client_ref.set_region(self.aws_region)
                userpool_client = up_client_ref.get_model_obj(self.paco_ctx.project)
                if up_client_ref.ref not in up_client_params:
                    up_client_name = self.create_cfn_logical_id(f'UserPoolClient{userpool_client.name}' + md5sum(str_data=up_client_ref.ref))
                    value = f'paco.ref {up_client_ref.ref }.id'
                    up_client_params[up_client_ref.ref] = self.create_cfn_parameter(
                        param_type='String',
                        name=up_client_name,
                        description=f'UserPool Client Id for {userpool_client.name}',
                        value=value,
                    )
                userpool = get_parent_by_interface(userpool_client, ICognitoUserPool)
                userpool_ref = userpool.paco_ref
                if userpool_ref not in up_params:
                    up_name = self.create_cfn_logical_id(f'UserPool{userpool.name}' + md5sum(str_data=userpool_ref))
                    up_params[userpool_ref] = self.create_cfn_parameter(
                        param_type='String',
                        name=up_name,
                        description=f'UserPool ProviderName for {userpool.name}',
                        value=userpool_ref + '.providername',
                    )
                idps.append({
                    "ClientId" : troposphere.Ref(up_client_params[up_client_ref.ref]),
                    "ProviderName" : troposphere.Ref(up_params[userpool_ref]),
                    "ServerSideTokenCheck" : idp.serverside_token_check,
                })
            cfn_export_dict['CognitoIdentityProviders'] = idps
        cip_resource = troposphere.cognito.IdentityPool.from_dict(
            'CognitoIdentityPool',
            cfn_export_dict
        )
        self.template.add_resource(cip_resource)

        # Outputs
        self.create_output(
            title=cip_resource.title + 'Id',
            description="Cognito Identity Pool Id",
            value=troposphere.Ref(cip_resource),
            ref=[cip.paco_ref_parts, cip.paco_ref_parts + ".id"],
        )

        # Roles
        roles_dict = {}

        unauthenticated_assume_role_policy = PolicyDocument(
            Statement=[
                Statement(
                    Effect=Allow,
                    Principal=Principal('Federated',"cognito-identity.amazonaws.com"),
                    Action=[Action('sts', 'AssumeRoleWithWebIdentity')],
                    Condition=Condition([
                        StringEquals({"cognito-identity.amazonaws.com:aud": troposphere.Ref(cip_resource)}),
                        ForAnyValueStringLike({"cognito-identity.amazonaws.com:amr": "unauthenticated"})
                    ]),
                ),
            ],
        )
        unauthenticated_role_resource = role_to_troposphere(
            cip.unauthenticated_role,
            'UnauthenticatedRole',
            assume_role_policy=unauthenticated_assume_role_policy,
        )
        if unauthenticated_role_resource != None:
            self.template.add_resource(unauthenticated_role_resource)
            roles_dict['unauthenticated'] = troposphere.GetAtt(unauthenticated_role_resource, "Arn")

        authenticated_assume_role_policy = PolicyDocument(
            Statement=[
                Statement(
                    Effect=Allow,
                    Principal=Principal('Federated',"cognito-identity.amazonaws.com"),
                    Action=[Action('sts', 'AssumeRoleWithWebIdentity')],
                    Condition=Condition([
                        StringEquals({"cognito-identity.amazonaws.com:aud": troposphere.Ref(cip_resource)}),
                        ForAnyValueStringLike({"cognito-identity.amazonaws.com:amr": "authenticated"})
                    ]),
                ),
            ],
        )
        authenticated_role_resource = role_to_troposphere(
            cip.authenticated_role,
            'AuthenticatedRole',
            assume_role_policy=authenticated_assume_role_policy
        )
        if authenticated_role_resource != None:
            self.template.add_resource(authenticated_role_resource)
            roles_dict['authenticated'] = troposphere.GetAtt(authenticated_role_resource, "Arn")

        # Identity Pool Role Attachment
        if roles_dict:
            iproleattachment_resource = troposphere.cognito.IdentityPoolRoleAttachment(
                title='IdentityPoolRoleAttachment',
                IdentityPoolId=troposphere.Ref(cip_resource),
                Roles=roles_dict,
            )
            self.template.add_resource(iproleattachment_resource)

"""
IAM User stack template

This is an application-level IAM User resource, for the global IAM Users stack template,
see paco/cftemplates/iam_users.py
"""

from awacs.aws import Allow, Action, Statement, PolicyDocument
from paco.models.references import get_model_obj_from_ref
from paco.cftemplates.cftemplates import StackTemplate
from paco.models import schemas
from paco import utils
import troposphere
import troposphere.iam
import awacs.ecr


class IAMUser(StackTemplate):
    def __init__(
        self,
        stack,
        paco_ctx,
    ):
        super().__init__(
            stack,
            paco_ctx,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
        )
        iamuser = stack.resource
        self.set_aws_name('IAMUser', self.resource_group_name, self.resource_name)

        # Init a Troposphere template
        self.init_template('IAM User')
        if not iamuser.is_enabled(): return

        # Parameters
        statements = []
        ecr_repo_allow = []
        for allow_ref in iamuser.allows:
            obj = get_model_obj_from_ref(allow_ref, self.paco_ctx.project)
            if schemas.IECRRepository.providedBy(obj):
                ecr_repo_allow.append(allow_ref)
            else:
                # Unsupported Allow ref
                if self.paco_ctx.warn:
                    print(f"The IAMUser resource:\n{iamuser.paco_ref_parts}\n" + \
                        f"does not support the resource:\n{allow_ref}\n" + \
                        f"{obj.type}\nIgnoring this reference."
                    )

        # Generate one statement for all ECR Repositories
        if len(ecr_repo_allow) > 0:
            ecr_arn_resources = []
            for allow_ref in ecr_repo_allow:
                ref_hash = utils.md5sum(str_data=allow_ref)
                ecr_arn_param = self.create_cfn_parameter(
                    name=self.create_cfn_logical_id('Allow' + ref_hash),
                    param_type='String',
                    description='Resource to allow access.',
                    value=allow_ref + '.arn',
                )
                ecr_arn_resources.append(troposphere.Ref(ecr_arn_param))

            statements.append(
                Statement(
                    Sid='ECRGetAuthorizationToken',
                    Effect=Allow,
                    Action=[
                        awacs.ecr.GetAuthorizationToken,
                    ],
                    Resource=['*'],
                ),
            )
            statements.append(
                Statement(
                    Sid='ECRAllowPushPull',
                    Effect=Allow,
                    Action=[
                        awacs.ecr.GetDownloadUrlForLayer,
                        awacs.ecr.BatchGetImage,
                        awacs.ecr.BatchCheckLayerAvailability,
                        awacs.ecr.PutImage,
                        awacs.ecr.InitiateLayerUpload,
                        awacs.ecr.UploadLayerPart,
                        awacs.ecr.CompleteLayerUpload
                    ],
                    Resource=ecr_arn_resources,
                ),
            )

        # Resources
        iam_user_dict = {}
        iamuser_resource = troposphere.iam.User.from_dict(
            'IAMUser',
            iam_user_dict
        )
        self.template.add_resource(iamuser_resource)

        if len(statements) > 0:
            user_policy_dict = {
                'PolicyDocument': PolicyDocument(
                        Version="2012-10-17",
                        Statement=statements,
                    ),
                'Users': [troposphere.Ref(iamuser_resource)]
            }
            user_policy_resource = troposphere.iam.ManagedPolicy.from_dict(
                'IAMUserPolicy',
                user_policy_dict
            )
            self.template.add_resource(user_policy_resource)
            self.create_output(
                title="IAMManagedPolicyArn",
                value=troposphere.Ref(user_policy_resource),
                ref=iamuser.paco_ref_parts + '.managedpolicy.arn',
            )

        # Outputs
        self.create_output(
            title="IAMUserUserName",
            value=troposphere.Ref(iamuser_resource),
            ref=iamuser.paco_ref_parts + '.username',
        )
        self.create_output(
            title="IAMUserArn",
            value=troposphere.GetAtt(iamuser_resource, 'Arn'),
            ref=iamuser.paco_ref_parts + '.arn',
        )


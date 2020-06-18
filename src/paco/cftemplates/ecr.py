from awacs.aws import Allow, Action, Principal, Statement, Condition, MultiFactorAuthPresent, PolicyDocument, StringEquals
from paco.cftemplates.cftemplates import StackTemplate
from paco.utils import prefixed_name
import troposphere
import troposphere.ecr


class ECRRepository(StackTemplate):
    def __init__(self, stack, paco_ctx):
        ecr_repository = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name('ECRRepository', self.resource_group_name, self.resource.name)

        self.init_template('Elastic Container Registry (ECR) Repository')
        if not ecr_repository.is_enabled(): return

        # Repository
        repo_dict = {
            'RepositoryName': ecr_repository.repository_name,
        }

        if ecr_repository.lifecycle_policy_text != None and ecr_repository.lifecycle_policy_text != "":
            repo_dict['LifecyclePolicy'] = troposphere.ecr.LifecyclePolicy(
                LifecyclePolicyText = ecr_repository.lifecycle_policy_text
            )
        if ecr_repository.repository_policy != None:
            policy_statements = []
            for policy_statement in ecr_repository.repository_policy.statement:
                statement_dict = {
                    'Effect': policy_statement.effect,
                    'Action': [
                        Action(*action.split(':')) for action in policy_statement.action
                    ]
                }
                if policy_statement.principal != None:
                    if len(policy_statement.principal.aws) > 0:
                        statement_dict['Principal'] = Principal("AWS", policy_statement.principal.aws)
                    elif len(policy_statement.principal.service) > 0:
                        statement_dict['Principal'] = Principal("Service", policy_statement.principal.service)
                policy_statements.append(
                    Statement(**statement_dict)
                )

            repo_dict['RepositoryPolicyText'] = PolicyDocument(
                Version="2012-10-17",
                Statement=policy_statements
            )
        repository_res = troposphere.ecr.Repository.from_dict(
            'Repository', repo_dict
        )

        # Outputs
        self.create_output(
            title=repository_res.title + 'Arn',
            description="ECR Repository Arn",
            value=troposphere.GetAtt(repository_res, 'Arn'),
            ref=ecr_repository.paco_ref_parts + ".arn")

        self.template.add_resource(repository_res)
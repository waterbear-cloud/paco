from aim.controllers.ctl_network_environment import NetEnvController
from aim.controllers.ctl_s3 import S3Controller
from aim.controllers.ctl_codecommit import CodeCommitController
from aim.controllers.ctl_route53 import Route53Controller
from aim.controllers.ctl_acm import ACMController
from aim.controllers.ctl_iam import IAMController
from aim.controllers.ctl_governance import GovernanceController
from aim.controllers.ctl_account import AccountController
from aim.controllers.ctl_project import ProjectController

klass = {
    'NetEnv': NetEnvController,
    'S3': S3Controller,
    'CodeCommit': CodeCommitController,
    'Route53': Route53Controller,
    'ACM': ACMController,
    'IAM': IAMController,
    'Governance': GovernanceController,
    'Account': AccountController,
    'Project': ProjectController
}
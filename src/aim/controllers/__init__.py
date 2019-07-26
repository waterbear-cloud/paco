from aim.controllers.ctl_network_environment import NetEnvController
from aim.controllers.ctl_s3 import S3Controller
from aim.controllers.ctl_codecommit import CodeCommitController
from aim.controllers.ctl_route53 import Route53Controller
from aim.controllers.ctl_acm import ACMController
from aim.controllers.ctl_iam import IAMController
from aim.controllers.ctl_account import AccountController
from aim.controllers.ctl_project import ProjectController
from aim.controllers.ctl_ec2 import EC2Controller
from aim.controllers.ctl_cloudwatch import CloudWatchController
from aim.controllers.ctl_lambda import LambdaController

klass = {
    'NetEnv': NetEnvController,
    'S3': S3Controller,
    'CodeCommit': CodeCommitController,
    'Route53': Route53Controller,
    'ACM': ACMController,
    'IAM': IAMController,
    'Account': AccountController,
    'Project': ProjectController,
    'EC2': EC2Controller,
    'CloudWatch': CloudWatchController,
    'Lambda': LambdaController
}
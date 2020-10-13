from paco.controllers.ctl_network_environment import NetEnvController
from paco.controllers.ctl_s3 import S3Controller
from paco.controllers.ctl_codecommit import CodeCommitController
from paco.controllers.ctl_route53 import Route53Controller
from paco.controllers.ctl_iam import IAMController
from paco.controllers.ctl_account import AccountController
from paco.controllers.ctl_project import ProjectController
from paco.controllers.ctl_ec2 import EC2Controller
from paco.controllers.ctl_cloudwatch import CloudWatchController
from paco.controllers.ctl_snstopics import SNTopicsGroupsController
from paco.controllers.ctl_cloudtrail import CloudTrailController
from paco.controllers.ctl_ssm import SSMController
from paco.controllers.ctl_config import ConfigController
from paco.controllers.ctl_sns import SNSController

klass = {
    'netenv': NetEnvController,
    's3': S3Controller,
    'codecommit': CodeCommitController,
    'route53': Route53Controller,
    'iam': IAMController,
    'account': AccountController, # deprecated
    'accounts': AccountController, # required to support `paco provision acocunts` command
    'project': ProjectController,
    'ec2': EC2Controller,
    'cloudwatch': CloudWatchController,
    'snstopics': SNTopicsGroupsController,
    'sns': SNSController,
    'cloudtrail': CloudTrailController,
    'ssm': SSMController,
    'config': ConfigController,
}

from paco.config.paco_context import PacoContext, AccountContext
from paco.core.exception import PacoException, StackException, InvalidPacoScope, PacoBaseException, InvalidPacoHome, InvalidVersionControl, \
    InvalidPacoConfigFile
from paco.core.yaml import YAML
from paco.models.exceptions import InvalidPacoProjectFile, UnusedPacoProjectField, InvalidPacoReference, InvalidAlarmConfiguration
from paco.models.references import get_model_obj_from_ref
from boto3.exceptions import Boto3Error
from botocore.exceptions import BotoCoreError, ClientError
from functools import wraps
import click
import os
import sys
import pathlib


yaml=YAML()
yaml.default_flow_sytle = False

pass_paco_context = click.make_pass_decorator(PacoContext, ensure=True)

config_types = """
CONFIG_SCOPE must be a Paco reference to a Paco object. This will select
a node of cloud resources to operate on. The CONFIG_SCOPE must start with
one of:

\b
  accounts
  netenv.<netenv-name>.<environment-name>[.<region>][.applications][.[<app-name>]
  resource.<global-resource-type>
  service.<add-on-name>

See the Paco CLI config scope docs at https://www.paco-cloud.io/en/latest//cli.html#config-scope

"""

def load_paco_config_options(paco_ctx):
    "Loads the .paco-work/config.yaml options"
    # read .pacoconfig
    config = None
    config_path = paco_ctx.home / '.pacoconfig'
    if config_path.exists():
        config = yaml.load(config_path)
    else:
        config_path = paco_ctx.paco_work_path / 'config.yml'
        # no config.yaml or config.yml, do nothing
        if not config_path.exists():
            return
        config_path = yaml.load(config_path)
    if 'warn' in config:
        if type(config['warn']) != type(bool()):
            raise InvalidPacoConfigFile("The 'warn' option must be a boolean in the paco config file at:\n{}.".format(config_path))
        paco_ctx.warn = config['warn']
    if 'verbose' in config:
        if type(config['verbose']) != type(bool()):
            raise InvalidPacoConfigFile("The 'verbose' option must be a boolean in the paco config file at:\n{}.".format(config_path))
        paco_ctx.verbose = config['verbose']

def init_cloud_command(
    command_name,
    paco_ctx,
    verbose,
    nocache,
    yes,
    warn,
    disable_validation,
    quiet_changes_only,
    config_scope,
    home
):
    "Applies cloud options and verifies that the command is sane. Loads the model and reports on it"""
    paco_ctx.verbose = verbose
    paco_ctx.nocache = nocache
    paco_ctx.yes = yes
    paco_ctx.warn = warn
    paco_ctx.disable_validation = disable_validation
    paco_ctx.quiet_changes_only = quiet_changes_only
    paco_ctx.command = command_name
    paco_ctx.config_scope = config_scope
    init_paco_home_option(paco_ctx, home)
    if not paco_ctx.home:
        raise InvalidPacoHome('Paco configuration directory needs to be specified with either --home or PACO_HOME environment variable.')

    load_paco_config_options(paco_ctx)

    # Inform about invalid scopes before trying to load the Paco project
    scopes = config_scope.split('.')
    if scopes[0] not in ('accounts', 'netenv', 'resource', 'service'):
        raise InvalidPacoScope(
"""'{}' is not a valid top-level CONFIG_SCOPE for '{}'. This must start with one of: accounts, netenv, resource or service.

See the Paco CLI config scope docs at https://www.paco-cloud.io/en/latest//cli.html#config-scope
""".format(scopes[0], config_scope)
        )

    if config_scope.startswith('accounts.'):
        raise InvalidPacoScope(
"""The accounts scope can only refer to the top-level 'accounts' and applies account actions
to all accounts listed in the organization_account_ids: field in the 'accounts/master.yaml' file.

See the Paco CLI config scope docs at https://www.paco-cloud.io/en/latest//cli.html#config-scope
"""
        )

    if config_scope.startswith('netenv'):
        parts = config_scope.split('.')
        if len(parts) < 3:
            raise InvalidPacoScope(
"""A netenv CONFIG_SCOPE must specify a minimum of a NetworkEnvironment name and Environment name, for example:

  netenv.mynet.dev
  netenv.mynet.prod
  netenv.mynet.prod.us-west-2
  netenv.mynet.test.us-west-2.applications.myapp
  netenv.mynet.test.us-west-2.applications.myapp.groups.cicd
  netenv.mynet.test.us-west-2.applications.myapp.groups.servers.resources.web

See the Paco CLI config scope docs at https://www.paco-cloud.io/en/latest//cli.html#config-scope
"""
            )

    if config_scope.startswith('resource'):
        parts = config_scope.split('.')
        if len(parts) == 1:
            raise InvalidPacoScope(
"""A resource CONFIG_SCOPE must specify a minimum of a global Resource type, for example:

  resource.codecommit
  resource.ec2

See the Paco CLI config scope docs at https://www.paco-cloud.io/en/latest//cli.html#config-scope
"""
            )

    if config_scope.lower().startswith('resource.codecommit'):
        parts = config_scope.split('.')
        if len(parts) > 2:
            raise InvalidPacoScope(
"""A CodeCommit Resource CONFIG_SCOPE can only apply to all CodeCommit repos:

  resource.codecommit

See the Paco CLI config scope docs at https://www.paco-cloud.io/en/latest//cli.html#config-scope
"""
            )

    if config_scope.lower().startswith('resource.snstopics'):
        parts = config_scope.split('.')
        if len(parts) > 2:
            raise InvalidPacoScope(
"""An SNSTopics resource CONFIG_SCOPE can only apply to all SNS Topics:

  resource.snstopics

See the Paco CLI config scope docs at https://www.paco-cloud.io/en/latest//cli.html#config-scope
"""
        )

    if config_scope.lower().startswith('resource.route53'):
        parts = config_scope.split('.')
        if len(parts) > 2:
            raise InvalidPacoScope(
"""A Route 53 resource CONFIG_SCOPE can only apply to all Route 53 configuration:

  resource.route53

See the Paco CLI config scope docs at https://www.paco-cloud.io/en/latest//cli.html#config-scope
"""
            )

    if config_scope.lower().startswith('resource.s3'):
        parts = config_scope.split('.')
        if len(parts) > 2:
            raise InvalidPacoScope(
"""A S3 resource CONFIG_SCOPE can only apply to all S3 Buckets:

  resource.s3

See the Paco CLI config scope docs at https://www.paco-cloud.io/en/latest//cli.html#config-scope
"""
            )

    paco_ctx.load_project()

    # Perform VCS checks if enforce_branch_environments is enabled
    if paco_ctx.project.version_control.enforce_branch_environments:
        vc_config = paco_ctx.project.version_control
        # Import git and test if it can find a valid git
        try:
            from git import Repo as GitRepo
            from git.exc import InvalidGitRepositoryError
        except ImportError:
            raise InvalidVersionControl("""This Paco project has version_control.enforce_branch_environments enabled in it's project.yaml file.
Could not find a git executable. Either disable or git must be included in your $PATH or set via $GIT_PYTHON_GIT_EXECUTABLE.""")

        try:
            repo = GitRepo(paco_ctx.home, search_parent_directories=False)
            branch_name =  repo.active_branch.name
        except InvalidGitRepositoryError:
            raise InvalidVersionControl("""This Paco project has version_control.enforce_branch_environments enabled in it's project.yaml file.
This Paco project is not under version control? Either put the project into a git repo or disable enforce_branch_environments.""")
        except TypeError:
            raise InvalidVersionControl("""This Paco project has version_control.enforce_branch_environments enabled in it's project.yaml file.
Unable to retrieve the current git branch name. This can occur when git is in a detached-head state. Either disable enforce_branch_environments or change your git state.""")

        # set-up override mappings
        mappings = {}
        for mapping in vc_config.git_branch_environment_mappings:
            environment, branch = mapping.split(':')
            mappings[environment]= branch

        # check branch vs netenv environment to see if they match
        if config_scope.startswith('netenv.'):
            env_name = config_scope.split('.')[2]
            if env_name in mappings:
                expected_branch_name = mappings[env_name]
            else:
                expected_branch_name = vc_config.environment_branch_prefix + env_name
            if expected_branch_name != branch_name:
                raise InvalidVersionControl("""This Paco project has version_control.enforce_branch_environments enabled in it's project.yaml file.
Expected to be on branch named '{}' for environment '{}', but the active branch is '{}'.""".format(
                    expected_branch_name, env_name, branch_name
                )
            )
        # or if outside a netenv check against the global environment name
        else:
            expected_branch_name = vc_config.environment_branch_prefix + vc_config.global_environment_name
            if branch_name != expected_branch_name:
                raise InvalidVersionControl("""This Paco project has version_control.enforce_branch_environments enabled in it's project.yaml file.
Expected to be on branch named '{}' for a change with a global scope of '{}', but the active branch is '{}'.""".format(
                    expected_branch_name, config_scope, branch_name
                ))

    scope_parts = config_scope.split('.')
    if scope_parts[0] == 'resource':
        controller_type = scope_parts[1]
    else:
        controller_type = scope_parts[0]

    paco_ref = 'paco.ref {}'.format(config_scope)
    obj = get_model_obj_from_ref(paco_ref, paco_ctx.project)
    return controller_type, obj

def cloud_options(func):
    """
    decorator to add cloud options
    """
    func = click.option(
        '-v', '--verbose',
        is_flag=True,
        default=False,
        help='Enables verbose mode.'
    )(func)
    func = click.option(
        '-n', '--nocache',
        is_flag=True,
        default=False,
        help='Disables the Paco CloudFormation stack cache.'
    )(func)
    func = click.option(
        '-y', '--yes',
        is_flag=True,
        default=False,
        help='Responds "yes" to any Yes/No prompts.'
    )(func)
    func = click.option(
        '-w', '--warn',
        is_flag=True,
        default=False,
        help='Warn about potential problems, such as invalid IAM Policies.'
    )(func)
    func = click.option(
        '-d', '--disable-validation',
        is_flag=True,
        default=False,
        help='Supresses validation differences.'
    )(func)
    func = click.option(
        '-c', '--quiet-changes-only',
        is_flag=True,
        default=False,
        help='Supresses Cache, Protected, and Disabled messages.'
    )(func)
    return func

def cloud_args(func):
    func = click.argument("CONFIG_SCOPE", required=True, type=click.STRING)(func)
    return func


def paco_home_option(func):
    """
    decorater to add Paco Home option
    """
    func = click.option(
        "--home",
        type=click.Path(exists=True, file_okay=False, resolve_path=True),
        help="Path to a Paco project configuration folder. Can also be set with the environment variable PACO_HOME.",
    )(func)
    return func

def init_paco_home_option(ctx, home):
    # --home overrides the PACO_HOME Env var
    if not home:
        home = os.environ.get('PACO_HOME')
    if home is not None:
        ctx.home = pathlib.Path(home)

def handle_exceptions(func):
    """
    Catches exceptions and displays errors in a human readable format
    """
    @wraps(func)
    def decorated(*args, **kwargs):
        # return func(*args, **kwargs)
        try:
            # new Paco Error types will be caught here
            # but they should be handled in the except clause
            return func(*args, **kwargs)
        except (
            InvalidPacoScope,
            InvalidPacoReference,
            UnusedPacoProjectField,
            InvalidPacoProjectFile,
            InvalidAlarmConfiguration,
            PacoException,
            PacoBaseException,
            StackException,
            BotoCoreError,
            ClientError,
            Boto3Error
        ) as error:
            error_name = error.__class__.__name__
            if hasattr(error, 'title'):
                error_title = error.title
            else:
                error_title = error_name
            click.echo("\033[1m\nERROR: {}\033[0m\n".format(error_title))

            if error_name in ('InvalidPacoProjectFile', 'UnusedPacoProjectField', 'InvalidPacoReference'):
                # Click fixme: in paco init commands args[0] doesn't get set so home is stashed in a global var
                if len(args) == 0:
                    home = os.environ.get('PACO_HOME')
                else:
                    home = args[0].home
                click.echo("Invalid Paco project configuration files at {}".format(home))
                if hasattr(error, 'args'):
                    if len(error.args) > 0:
                        click.echo(error.args[0])
            elif error_name in ('StackException'):
                click.echo(error.message)
            # generically catch new-style exceptions last
            elif isinstance(error, PacoBaseException):
                click.echo(error)
            elif isinstance(error, PacoException):
                click.echo(error.code)
            else:
                if hasattr(error, 'message'):
                    click.echo(error.message)
                else:
                    click.echo(error)
            print('')
            sys.exit(1)

    return decorated

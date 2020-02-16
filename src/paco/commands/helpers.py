import click
import os
import sys
import ruamel.yaml.constructor
from paco.config.paco_context import PacoContext, AccountContext
from paco.core.exception import PacoException, StackException, InvalidPacoScope, PacoBaseException, InvalidPacoHome
from paco.models.exceptions import InvalidPacoProjectFile, UnusedPacoProjectField, InvalidPacoReference
from paco.models.references import get_model_obj_from_ref
from boto3.exceptions import Boto3Error
from botocore.exceptions import BotoCoreError, ClientError
from functools import wraps

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

def init_cloud_command(
    command_name,
    paco_ctx,
    verbose,
    nocache,
    yes,
    disable_validation,
    quiet_changes_only,
    config_scope,
    home
):
    paco_ctx.verbose = verbose
    paco_ctx.nocache = nocache
    paco_ctx.yes = yes
    paco_ctx.disable_validation = disable_validation
    paco_ctx.quiet_changes_only = quiet_changes_only
    paco_ctx.command = command_name
    init_paco_home_option(paco_ctx, home)
    if not paco_ctx.home:
        raise InvalidPacoHome('Paco configuration directory needs to be specified with either --home or PACO_HOME environment variable.')

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

    if config_scope.lower().startswith('resource.snstopics') or config_scope.lower().startswith('resource.notificationgroups'):
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

    import warnings
    warnings.simplefilter("ignore")
    paco_ctx.load_project()

    # resource.snstopics is an alias for resource.notificationgroups
    if config_scope.startswith('resource.snstopics'):
        config_scope = 'resource.notificationgroups' + config_scope[len('resource.snstopics'):]

    scope_parts = config_scope.split('.')
    if scope_parts[0] == 'resource':
        controller_type = scope_parts[1]
    else:
        controller_type = scope_parts[0]

    # Locate a model object and summarize it
    paco_ref = 'paco.ref {}'.format(config_scope)
    obj = get_model_obj_from_ref(paco_ref, paco_ctx.project)
    print('Object selected to {}:'.format(command_name))
    print('  Name: {}'.format(
        getattr(obj, 'name', 'unnamed')
    ))
    print('  Type: {}'.format(obj.__class__.__name__))
    if getattr(obj, 'title', None):
        print('  Title: {}'.format(obj.title))
    if hasattr(obj, 'paco_ref_parts'):
        print('  Reference: {}'.format(obj.paco_ref_parts))

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
        help="Path to an Paco project configuration folder. Can also be set with the environment variable PACO_HOME.",
    )(func)
    return func

def init_paco_home_option(ctx, home):
    # --home overrides the PACO_HOME Env var
    if not home:
        home = os.environ.get('PACO_HOME')
    if home is not None:
        ctx.home = home

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
                    home = PACO_HOME
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

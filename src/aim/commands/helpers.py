import click
import os
import sys
from aim.config.aim_context import AimContext, AccountContext
from aim.core.exception import AimException, StackException
from aim.models.exceptions import InvalidAimProjectFile, UnusedAimProjectField, InvalidAimReference
from aim.models.references import get_model_obj_from_ref
from boto3.exceptions import Boto3Error
from botocore.exceptions import BotoCoreError, ClientError
from functools import wraps

pass_aim_context = click.make_pass_decorator(AimContext, ensure=True)

config_types = """
CONFIG_SCOPE must be an AIM Reference to an AIM object. These can be
constructed by matching a top-level directory name, with a filename
and then optionally walking through keys within that file. Each
part is separated by the . character.

\b
  account. objects : AWS Accounts
    Location: files in the `Accounts` directory.
    Examples:
      accounts.dev
      accounts.master

\b
  resource. objects : Global Resources
    Location: files in the `Resources` directory.
    examples:
      resource.ec2.keypairs.mykeypair
      resource.cloudtrail
      resource.codecommit
      resource.iam

\b
  netenv. objects : NetworkEnvironments
    Location: files in the `NetworkEnvironments` directory.
    examlpes:
      netenv.mynet.dev
      netenv.mynet.dev.us-west-2
      netenv.mynet.dev.us-west-2.applications.myapp.groups.somegroup.resources.webserver

\b
  service. objects : AIM Pluggable Extensions
    Location: files in the `Services` directory.
    examples:
      service.notification
      service.security

"""

def init_cloud_command(
    command_name,
    aim_ctx,
    verbose,
    nocache,
    yes,
    disable_validation,
    quiet_changes_only,
    config_scope,
    home
):
    aim_ctx.verbose = verbose
    aim_ctx.nocache = nocache
    aim_ctx.yes = yes
    aim_ctx.disable_validation = disable_validation
    aim_ctx.quiet_changes_only = quiet_changes_only
    aim_ctx.command = command_name
    init_aim_home_option(aim_ctx, home)
    if not aim_ctx.home:
        print('AIM configuration directory needs to be specified with either --home or AIM_HOME environment variable.')
        sys.exit()
    aim_ctx.load_project()
    scope_parts = config_scope.split('.')
    if scope_parts[0] == 'resource':
        controller_type = scope_parts[1]
    else:
        controller_type = scope_parts[0]

    # Locate a model object and summarize it
    aim_ref = 'aim.ref {}'.format(config_scope)
    obj = get_model_obj_from_ref(aim_ref, aim_ctx.project)
    print('Object selected to {}:'.format(command_name))
    print('  Name: {}'.format(
        getattr(obj, 'name', 'unnamed')
    ))
    print('  Type: {}'.format(obj.__class__.__name__))
    if getattr(obj, 'title', None):
        print('  Title: {}'.format(obj.title))
    if hasattr(obj, 'aim_ref_parts'):
        print('  Reference: {}'.format(obj.aim_ref_parts))

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
        help='Disables the AIM CloudFormation stack cache.'
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


def aim_home_option(func):
    """
    decorater to add AIM Home option
    """
    func = click.option(
        "--home",
        type=click.Path(exists=True, file_okay=False, resolve_path=True),
        help="Path to an AIM Project configuration folder. Can also be set with the environment variable AIM_HOME.",
    )(func)
    return func

def init_aim_home_option(ctx, home):
    # --home overrides the AIM_HOME Env var
    if not home:
        home = os.environ.get('AIM_HOME')
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
            return func(*args, **kwargs)
        except (InvalidAimReference, UnusedAimProjectField, InvalidAimProjectFile, AimException, StackException, BotoCoreError,
            ClientError, Boto3Error) as error:
            click.echo("\nERROR!\n")
            error_name = error.__class__.__name__
            if error_name in ('InvalidAimProjectFile', 'UnusedAimProjectField', 'InvalidAimReference'):
                click.echo("Invalid AIM project configuration files at {}".format(args[0].home))
                if hasattr(error, 'args'):
                    if len(error.args) > 0:
                        click.echo(error.args[0])
            elif error_name in ('StackException'):
                click.echo(error.message)
            else:
                if hasattr(error, 'message'):
                    click.echo(error.message)
                else:
                    click.echo(error)
            print('')
            sys.exit(1)

    return decorated

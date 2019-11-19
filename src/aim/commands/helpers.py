import click
import os
import sys
from aim.config.aim_context import AimContext, AccountContext
from aim.core.exception import AimException, StackException
from aim.models.exceptions import InvalidAimProjectFile, UnusedAimProjectField, InvalidAimReference
from boto3.exceptions import Boto3Error
from botocore.exceptions import BotoCoreError, ClientError
from functools import wraps

pass_aim_context = click.make_pass_decorator(AimContext, ensure=True)

config_types = """
CONFIG_TYPE and CONFIG_SCOPE must be:

\b
  Account resources
    CONFIG_TYPE: account
    CONFIG_SCOPE: filename in the `Accounts` directory.

\b
  Global resources
    CONFIG_TYPE: resource
    CONFIG_SCOPE: filename in the `Resources` directory.
    examples:
      resource ec2.keypairs.mykeypair
      resource cloudtrail
      resource codecommit
      resource iam

\b
  NetworkEnvironment resources
    CONFIG_TYPE: netenv
    CONFIG_SCOPE: filename in the `NetworkEnvironments` directory and dotted scope within that file.
      The dotted filename is in the format: <netenv_name>.<environment_name>.<region>
    examlpes:
      netenv mynet.dev
      netenv mynet.dev.us-west-2
      netenv mynet.dev.us-west-2.applications.myapp.groups.somegroup.resources.webserver

\b
  Service resources
    CONFIG_TYPE: service
    CONFIG_SCOPE: filename in the `Services` directory.
    examples:
      service notification
      service security

"""

def set_cloud_options(
    command_name,
    aim_ctx,
    verbose,
    nocache,
    yes,
    disable_validation,
    quiet_changes_only,
    config_type,
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
    if config_type == 'resource':
        controller_type = config_scope.split('.')[0]
        controller_args = {
            'command': command_name,
            'arg_1': controller_type,
            'arg_2': config_scope,
            'arg_3': None,
            'arg_4': None
        }
    else:
        controller_type = config_type
        controller_args = {
            'command': command_name,
            'arg_1': config_scope,
            'arg_2': None,
            'arg_3': None,
            'arg_4': None
        }
    return controller_type, controller_args

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
    func = click.argument("config_scope", required=True, type=click.STRING)(func)
    func = click.argument("config_type", required=True, type=click.STRING)(func)
    return func

def controller_args(func):
    """
    decorator to add controller args
    """
    func = click.argument("arg_4", required=False, type=click.STRING)(func)
    func = click.argument("arg_3", required=False, type=click.STRING)(func)
    func = click.argument("arg_2", required=False, type=click.STRING)(func)
    func = click.argument("arg_1", required=False, type=click.STRING)(func)
    func = click.argument("controller_type", required=True, type=click.STRING)(func)
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

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
        return func(*args, **kwargs)
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
            sys.exit(1)

    return decorated

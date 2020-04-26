import paco.models
import click
import sys
from paco.commands.helpers import (
    paco_home_option, init_paco_home_option, pass_paco_context,
    handle_exceptions, cloud_options, init_cloud_command, cloud_args, config_types
)
from paco.core.exception import StackException

@click.group(name="lambda")
@pass_paco_context
def lambda_group(paco_ctx):
    command = 'lambda'

lambda_group.help = """
Manage Lambda function(s).

"""

@lambda_group.command(name="deploy")
@cloud_args
@cloud_options
@paco_home_option
@click.pass_context
@handle_exceptions
def lambda_deploy(
    ctx,
    verbose,
    nocache,
    yes,
    warn,
    disable_validation,
    quiet_changes_only,
    config_scope,
    home='.',
):
    """
    Deploy Lambda code to AWS.
    """
    paco_ctx = ctx.obj
    command = 'lambda deploy'
    controller_type, obj = init_cloud_command(
        command,
        paco_ctx,
        verbose,
        nocache,
        yes,
        warn,
        disable_validation,
        quiet_changes_only,
        config_scope,
        home
    )
    controller = paco_ctx.get_controller(controller_type, command, obj)
    controller.lambda_deploy_command(obj)

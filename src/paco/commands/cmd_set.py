import paco.models
import click
import sys
from paco.commands.helpers import (
    paco_home_option, init_paco_home_option, pass_paco_context,
    handle_exceptions, cloud_options, init_cloud_command, cloud_args, config_types
)
from paco.core.exception import StackException


@click.command(name='set', short_help='Sets the value of a resource.')
@paco_home_option
@cloud_args
@cloud_options
@pass_paco_context
@handle_exceptions
def set_command(
    paco_ctx,
    verbose,
    nocache,
    yes,
    warn,
    disable_validation,
    quiet_changes_only,
    hooks_only,
    cfn_lint,
    config_scope,
    home='.',
):
    """Set the value of a cloud resource"""
    command = 'set'
    controller_type, obj = init_cloud_command(
        command,
        paco_ctx,
        verbose,
        nocache,
        yes,
        warn,
        disable_validation,
        quiet_changes_only,
        hooks_only,
        cfn_lint,
        config_scope,
        home
    )
    controller = paco_ctx.get_controller(controller_type, command, obj)
    controller.set_command(obj)

set_command.help = """
Set the value of a cloud resource.

""" + config_types

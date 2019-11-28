import paco.models
import click
import sys
from paco.commands.helpers import (
    paco_home_option, init_paco_home_option, pass_paco_context,
    handle_exceptions, cloud_options, init_cloud_command, cloud_args, config_types
)
from paco.core.exception import StackException


@click.command(name='provision', short_help='Provision resources to the cloud.')
@paco_home_option
@cloud_args
@cloud_options
@pass_paco_context
@handle_exceptions
def provision_command(
    paco_ctx,
    verbose,
    nocache,
    yes,
    disable_validation,
    quiet_changes_only,
    config_scope,
    home='.'
):
    """Provision AWS Resources"""
    command = 'provision'
    controller_type, obj = init_cloud_command(
        command,
        paco_ctx,
        verbose,
        nocache,
        yes,
        disable_validation,
        quiet_changes_only,
        config_scope,
        home
    )
    controller = paco_ctx.get_controller(controller_type, command, obj)
    controller.provision()

provision_command.help = """
Provision AWS Resources.

""" + config_types
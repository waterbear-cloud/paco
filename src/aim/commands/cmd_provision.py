import aim.models
import click
import sys
from aim.commands.helpers import (
    controller_args, aim_home_option, init_aim_home_option, pass_aim_context,
    handle_exceptions, cloud_options, set_cloud_options, cloud_args, config_types
)
from aim.core.exception import StackException


@click.command(name='provision', short_help='Provision resources to the cloud.')
@aim_home_option
@cloud_args
@cloud_options
@pass_aim_context
@handle_exceptions
def provision_command(
    aim_ctx,
    verbose,
    nocache,
    yes,
    disable_validation,
    quiet_changes_only,
    config_type,
    config_scope,
    home='.'
):
    """Provision AWS Resources"""
    controller_type, controller_args = set_cloud_options(
        'provision',
        aim_ctx,
        verbose,
        nocache,
        yes,
        disable_validation,
        quiet_changes_only,
        config_type,
        config_scope,
        home
    )
    controller = aim_ctx.get_controller(controller_type, controller_args)
    controller.provision()

provision_command.help = """
Provision AWS Resources.

""" + config_types
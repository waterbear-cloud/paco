import paco.models
import click
import sys
from paco.commands.helpers import (
    paco_home_option, init_paco_home_option, pass_paco_context,
    handle_exceptions, cloud_options, init_cloud_command, cloud_args, config_types
)
from paco.core.exception import StackException


@click.command('delete', short_help='Delete Paco managed resources')
@paco_home_option
@cloud_args
@cloud_options
@pass_paco_context
@handle_exceptions
def delete_command(
    paco_ctx,
    verbose,
    nocache,
    yes,
    warn,
    disable_validation,
    quiet_changes_only,
    config_scope,
    home='.'
):
    """Deletes provisioned Cloud Resources"""
    command = 'delete'
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
    answer = paco_ctx.input_confirm_action("Proceed with deletion of {}?".format(config_scope))
    if answer == False:
        print("Aborted delete operation.")
        return

    controller = paco_ctx.get_controller(controller_type, 'delete', obj)
    controller.delete()

delete_command.help = """
Delete cloud resources.

""" + config_types

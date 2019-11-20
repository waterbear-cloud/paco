import aim.models
import click
import sys
from aim.commands.helpers import (
    controller_args, aim_home_option, init_aim_home_option, pass_aim_context,
    handle_exceptions, cloud_options, set_cloud_options, cloud_args, config_types
)
from aim.core.exception import StackException
from aim.models.references import get_model_obj_from_ref


@click.command('delete', short_help='Delete AIM managed resources')
@aim_home_option
@cloud_args
@cloud_options
@pass_aim_context
@handle_exceptions
def delete_command(
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
    """Deletes provisioned AWS Resources"""
    controller_type, controller_args = set_cloud_options(
        'delete',
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
    aim_ref = 'aim.ref {}.{}'.format(config_type, config_scope)
    obj = get_model_obj_from_ref(aim_ref, aim_ctx.project)
    print('Resource selected for deletion:')
    print('  Type: {}'.format(obj.__class__.__name__))
    print('  Name: {}'.format(obj.name))
    if getattr(obj, 'title', None):
        print('  Title: {}'.format(obj.title))
    print('  Reference: {}'.format(obj.aim_ref))
    answer = aim_ctx.input_confirm_action("Proceed with deletion of {} {}?".format(config_type, config_scope))
    if answer == False:
        print("Aborted delete operation.")
        return

    controller = aim_ctx.get_controller(controller_type, controller_args)
    controller.delete()

delete_command.help = """
Delete cloud resources.

""" + config_types

import aim.models
import click
import sys
from aim.commands.helpers import pass_aim_context, controller_args, aim_home_option, init_aim_home_option, handle_exceptions
from aim.core.exception import StackException


@click.command('delete', short_help='Delete AIM managed resources')
@controller_args
@aim_home_option
@pass_aim_context
@handle_exceptions
def delete_command(aim_ctx, controller_type, arg_1=None, arg_2=None, arg_3=None, arg_4=None, home='.'):
    """Deletes provisioned AWS Resources"""
    aim_ctx.command = 'delete'
    init_aim_home_option(aim_ctx, home)
    if not aim_ctx.home:
        print('AIM configuration directory needs to be specified with either --home or AIM_HOME environment variable.')
        sys.exit()

    delete_name = "{0} {1}".format(controller_type, arg_1)
    if arg_2:
        delete_name += " {0}".format(arg_2)

    answer = aim_ctx.input_confirm_action("Proceed with deletion?")
    if answer == False:
        print("Aborted delete operation.")
        return

    aim_ctx.log("Delete: Controller: {}  arg_1({}) arg_2({}) arg_3({}) arg_4({})".format(controller_type, arg_1, arg_2, arg_3, arg_4) )
    aim_ctx.load_project()

    controller_args = {
        'command': 'delete',
        'arg_1': arg_1,
        'arg_2': arg_2,
        'arg_3': arg_3,
        'arg_4': arg_4
    }
    controller = aim_ctx.get_controller(controller_type, controller_args)
    controller.delete()

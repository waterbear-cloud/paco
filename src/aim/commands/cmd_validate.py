import click
import sys
from aim.core.exception import StackException
from aim.commands.helpers import pass_aim_context, controller_args, aim_home_option, init_aim_home_option, handle_exceptions

@click.command('validate', short_help='Validate an AIM project')
@controller_args
@aim_home_option
@pass_aim_context
@handle_exceptions
def validate_command(aim_ctx, controller_type, arg_1=None, arg_2=None, arg_3=None, arg_4=None, home='.'):
    """Validates a Config CloudFormation"""

    aim_ctx.command = 'validate'
    init_aim_home_option(aim_ctx, home)
    if not aim_ctx.home:
        print('AIM configuration directory needs to be specified with either --home or AIM_HOME environment variable.')
        sys.exit()

    aim_ctx.log("Validate: Controller: {}  arg_1({}) arg_2({}) arg_3({}) arg_4({})".format(controller_type, arg_1, arg_2, arg_3, arg_4) )

    aim_ctx.load_project()
    controller_args = {
        'command': 'validate',
        'arg_1': arg_1,
        'arg_2': arg_2,
        'arg_3': arg_3,
        'arg_4': arg_4
    }
    controller = aim_ctx.get_controller(controller_type, controller_args)
    controller.validate()

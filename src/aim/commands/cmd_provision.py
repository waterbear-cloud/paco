import aim.models
import click
import sys
from aim.commands.helpers import controller_args, aim_home_option, init_aim_home_option, pass_aim_context, handle_exceptions
from aim.core.exception import StackException

@click.command(name='provision', short_help='Provision an AIM project or a specific environment.')
@controller_args
@aim_home_option
@pass_aim_context
@handle_exceptions
def provision_command(aim_ctx, controller_type, component_name=None, config_name=None, config_region=None, home='.'):
    """Provision AWS Resources"""
    init_aim_home_option(aim_ctx, home)
    if not aim_ctx.home:
        print('AIM configuration directory needs to be specified with either --home or AIM_HOME environment variable.')
        sys.exit()
    aim_ctx.log("Provisioning Configuration: %s.%s", controller_type, component_name )
    aim_ctx.init_project()
    #aim_ctx.config_processor.apply()
    config_arg = None
    if controller_type == "NetEnv":
        config_arg = {
            'netenv_id': component_name,
            'subenv_id': config_name,
            'region' : config_region
        }
    elif controller_type == "EC2":
        config_arg = {
            'service': component_name,
            'id': config_name
        }
    else:
        config_arg = {
            'name': component_name
        }

    controller = aim_ctx.get_controller(controller_type, config_arg)
    controller.provision()

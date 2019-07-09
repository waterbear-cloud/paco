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
def delete_command(aim_ctx, controller_type, component_name=None, config_name=None, config_region=None, home='.'):
    """Deletes provisioned AWS Resources"""
    init_aim_home_option(aim_ctx, home)
    if not aim_ctx.home:
        print('AIM configuration directory needs to be specified with either --home or AIM_HOME environment variable.')
        sys.exit()

    #project = aim.models.load_project_from_yaml(aim_ctx.home)
    #aim_obj = project.find_object_from_cli(
    #    controller_type,
    #    component_name,
    #    config_name
    #)
    delete_name = "{0} {1}".format(controller_type, component_name)
    if config_name:
        delete_name += " {0}".format(config_name)
    #print("This will delete {} - (model: {} - {})".format(delete_name, aim_obj.name, aim_obj.title))
    answer = input("Proceed with deletion (y/N)? ")
    if answer.lower() != 'y':
        print("Aborting delete operation")
        return

    aim_ctx.log("Deleting: %s.%s", controller_type, component_name )

    aim_ctx.init_project()
    if controller_type == "NetEnv":
        config_arg = {
            'netenv_id': component_name,
            'subenv_id': config_name,
            'region': config_region
        }
    elif controller_type == "EC2":
        config_arg = {
            'service': component_name,
            'id': config_name
        }
    else:
        config_arg = component_name

    controller = aim_ctx.get_controller(controller_type, config_arg)
    controller.delete()

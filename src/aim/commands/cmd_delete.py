import click
import aim.models
from aim.commands.cli import pass_context
from aim.core.exception import StackException


@click.command('delete', short_help='Delete AIM managed resources')
@click.argument('controller_type', required=True, type=click.STRING)
@click.argument('component_name', required=True, type=click.STRING)
@click.argument('config_name', required=False, type=click.STRING)
@click.argument('config_region', required=False, type=click.STRING)
@pass_context
def cli(aim_ctx, controller_type, component_name=None, config_name=None, config_region=None):
    """Deletes provisioned AWS Resources"""
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

    aim_ctx.init_project(aim_ctx.home)
    if controller_type == "NetEnv":
        config_arg = {
            'netenv_id': component_name,
            'subenv_id': config_name,
            'region': config_region
        }
    else:
        config_arg = component_name

    controller = aim_ctx.get_controller(controller_type, config_arg)
    controller.delete()

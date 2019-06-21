import aim.models
import click
from aim.commands.cli import pass_context
from aim.core.exception import StackException


@click.command('provision', short_help='Provision an AIM project or a specific environment.')
@click.argument('controller_type', required=True, type=click.STRING)
@click.argument('component_name', required=False, type=click.STRING)
@click.argument('config_name', required=False, type=click.STRING)
@click.argument('config_region', required=False, type=click.STRING)
@pass_context
def cli(aim_ctx, controller_type, component_name=None, config_name=None, config_region=None):
    """Provision AWS Resources"""
    #project = aim.models.load_project_from_yaml(aim_ctx.home)
    #aim_obj = project.find_object_from_cli(
    #    controller_type,
    #    component_name,
    #    config_name
    #)
    aim_ctx.log("Provisioning Configuration: %s.%s", controller_type, component_name )
    aim_ctx.init_project(aim_ctx.home)
    config_arg = None
    if controller_type == "NetEnv":
        config_arg = {
            'netenv_id': component_name,
            'subenv_id': config_name,
            'region' : config_region
        }
    else:
        config_arg = {
            'name': component_name
        }

    controller = aim_ctx.get_controller(controller_type, config_arg)
    controller.provision()

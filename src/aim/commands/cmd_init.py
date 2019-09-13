import click
import os
import os.path
import sys
from aim.commands.helpers import pass_aim_context, controller_args, aim_home_option, init_aim_home_option
from cookiecutter.main import cookiecutter
from jinja2.ext import Extension


def env_override(value, key):
    env_value = os.getenv(key, value)
    if env_value:
        return env_value
    else:
        return value

class EnvOverrideExtension(Extension):
    def __init__(self, environment):
        super(EnvOverrideExtension, self).__init__(environment)
        environment.filters['env_override'] = env_override

@click.command('init', short_help='Initializes AIM Project files', help="""
Initializes AIM Project files. The types of resources possible are:

 - project: Create the skeleton configuration directory and files
        for an empty or complete AIM Project.

""")
#@click.argument('controller_type', default='project', type=click.STRING)
#@click.option(
#    "-r",
#    "--region",
#    help="AWS region code, e.g. us-west-2",
#)
#@click.option(
#    "-k",
#    "--keypair_name",
#    help="EC2 keypair name",
#)
@aim_home_option
@controller_args
@pass_aim_context
def init_command(aim_ctx, controller_type, arg_1=None, arg_2=None, arg_3=None, arg_4=None, home='.'):
    """Initializes AIM Configuration"""
    aim_ctx.command = 'init'
    init_aim_home_option(aim_ctx, home)
    if not aim_ctx.home:
        print('AIM configuration directory needs to be specified with either --home or AIM_HOME environment variable.')
        sys.exit()

    aim_ctx.log("Init: Controller: {}  arg_1({}) arg_2({}) arg_3({}) arg_4({})".format(controller_type, arg_1, arg_2, arg_3, arg_4) )

    # If we are initializing the project, laod_project needs to behave differently
    project_init=False
    if controller_type == 'project' and arg_1 == None:
        project_init=True
    aim_ctx.load_project(project_init=project_init)

    controller_args = {
        'arg_1': arg_1,
        'arg_2': arg_2,
        'arg_3': arg_3,
        'arg_4': arg_4,
        'command': 'init'
    }
    controller = aim_ctx.get_controller(controller_type, controller_args)
    controller.init_command(controller_args)
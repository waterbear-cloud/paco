import click
import os
import os.path
import sys
import paco.commands.helpers
import pathlib
from paco.commands.helpers import paco_home_option, init_paco_home_option, handle_exceptions
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

def init_args(func):
    func = click.argument("ACTION", required=True, type=click.STRING)(func)
    return func

@click.group(name="init")
@click.pass_context
def init_group(paco_ctx):
    """
    Commands for initializing Paco projects.
    """
    pass

@init_group.command(name="project")
@click.argument("project-name")
@click.pass_context
def init_project(ctx, project_name):
    """
    Creates a new directory with a templated Paco project in it.
    """
    paco_ctx = ctx.obj
    paco_ctx.command = 'init project'

    # As we are initializing the project, laod_project needs to behave differently
    paco_ctx.home = pathlib.Path().cwd() / project_name
    paco_ctx.load_project(project_init=True)
    ctl_project = paco_ctx.get_controller('project')
    ctl_project.init_project()

@init_group.command(name="credentials")
@paco_home_option
@handle_exceptions
@click.pass_context
def init_credentials(ctx, home='.'):
    """
    Initializes the .credentials file for a Paco project.
    """
    paco_ctx = ctx.obj
    paco_ctx.command = 'init credentials'
    init_paco_home_option(paco_ctx, home)
    if paco_ctx.home == None:
        print("PACO_HOME or --home must be set.")
        sys.exit()
    paco.commands.helpers.PACO_HOME = paco_ctx.home
    paco_ctx.load_project(project_only=True)
    ctl_project = paco_ctx.get_controller('project')
    ctl_project.init_credentials()

@init_group.command(name="accounts")
@paco_home_option
@handle_exceptions
@click.pass_context
def init_accounts(ctx, home='.'):
    """
    Initializes the accounts for a Paco project.
    """
    paco_ctx = ctx.obj
    paco_ctx.command = 'init accounts'
    init_paco_home_option(paco_ctx, home)
    paco.commands.helpers.PACO_HOME = paco_ctx.home
    paco_ctx.load_project(master_only=True)
    ctl_project = paco_ctx.get_controller('project')
    ctl_project.init_accounts()

@init_group.command(name="netenv")
@paco_home_option
@click.pass_context
def init_netenv(ctx, home='.'):
    """
    Initializes a netenv resource for a Paco project.
    """
    paco_ctx = ctx.obj
    paco_ctx.command = 'init netenv'
    init_paco_home_option(paco_ctx, home)
    paco_ctx.load_project()
    ctl_project = paco_ctx.get_controller('project')
    # ToDo: FixMe! pass proper NetEnv info to init_command ...
    ctl_project.init_command()

import click
import sys
import aim.models
from aim.commands.helpers import pass_aim_context, aim_home_option, init_aim_home_option, handle_exceptions

@click.command('describe', short_help='Describe an AIM project')
@aim_home_option
@pass_aim_context
@handle_exceptions
def describe_command(ctx, home='.'):
    """Describe an AIM project"""
    init_aim_home_option(ctx, home)
    if not ctx.home:
        print('AIM configuration directory needs to be specified with either --home or AIM_HOME environment variable.')
        sys.exit()
    project = aim.models.load_project_from_yaml(ctx.home)

    print('Project: {} - {}'.format(project.name, project.title))
    print('Location: {}'.format(ctx.home))
    print()
    print('Accounts')
    for ne in project['accounts'].values():
        print(' - {} - {}'.format(ne.name, ne.title))
    print()
    print('Network Environments')
    for ne in project['ne'].values():
        print(' - {} - {}'.format(ne.name, ne.title))
    print()

import click
import sys
import aim.models
from aim.commands.cli import pass_context

@click.command('describe', short_help='Describe an AIM project')
@pass_context
def cli(ctx):
    """Describe an AIM project"""
    project = aim.models.load_project_from_yaml(ctx, ctx.home)
    try:
        project = aim.models.load_project_from_yaml(ctx, ctx.home)
    except AttributeError:
        print('AIM configuration directory needs to be specified with either --home or AIM_HOME environment variable.')
        sys.exit()

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

from paco.commands.helpers import pass_paco_context, paco_home_option, init_paco_home_option, handle_exceptions
from paco.commands.display import display_project_as_html
import click
import pathlib
import shutil


@click.command('describe', short_help='Describe a Paco project')
@paco_home_option
@pass_paco_context
@handle_exceptions
@click.option(
    '-o', '--output',
    default='html',
    help='Output format.'
)
@click.option(
    '-d', '--display',
    default='chrome',
    help='Display output in external app.'
)
def describe_command(paco_ctx, home='.', output='html', display='chrome'):
    """Describe a Paco project"""
    paco_ctx.command = 'describe'
    init_paco_home_option(paco_ctx, home)
    paco_ctx.load_project()
    project = paco_ctx.project
    static_path, html_files, envs_html = display_project_as_html(project)
    display_path = paco_ctx.display_path
    pathlib.Path(display_path).mkdir(parents=True, exist_ok=True)
    shutil.copytree(static_path, display_path, dirs_exist_ok=True)
    for fname, html in html_files.items():
        with open(str(display_path / fname), 'w') as fh:
            fh.write(html)
    for name, html in envs_html.items():
        with open(str(display_path / name), 'w') as fh:
            fh.write(html)

# paco describe --output=html --open=chrome

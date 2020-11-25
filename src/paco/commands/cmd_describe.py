from paco.commands.helpers import pass_paco_context, paco_home_option, init_paco_home_option, handle_exceptions
from paco.commands.display import display_project_as_html, display_project_as_json
from paco.core.exception import InvalidOption
import click
import json
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
    paco_ctx.skip_account_ctx = True
    layout_options = ('html', 'spa', 'json')
    if output not in layout_options:
        raise InvalidOption('Output option (-o, --output) can only be html, json or spa')
    init_paco_home_option(paco_ctx, home)
    paco_ctx.load_project(validate_local_paths=False)
    project = paco_ctx.project

    # Output HTML
    describe_path = pathlib.Path(paco_ctx.describe_path)
    describe_path.mkdir(parents=True, exist_ok=True)
    if output == 'html':
        static_path, html_files, envs_html = display_project_as_html(project, output)
        shutil.copytree(static_path, describe_path, dirs_exist_ok=True)
        for fname, html in html_files.items():
            with open(str(describe_path / fname), 'w') as fh:
                fh.write(html)
        for name, html in envs_html.items():
            with open(str(describe_path / name), 'w') as fh:
                fh.write(html)

    # Output JSON
    if output in ('json', 'spa'):
        json_docs = display_project_as_json(project)
        for key, value in json_docs.items():
            with open(str(describe_path / f'{key}.json'), 'w') as fh:
                fh.write(json.dumps(value))


# paco describe --output=html --open=chrome

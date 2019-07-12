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
@click.argument('config_type', default='project', type=click.STRING)
@click.option(
    "-r",
    "--region",
    help="AWS region code, e.g. us-west-2",
)
@click.option(
    "-k",
    "--keypair_name",
    help="EC2 keypair name",
)
@aim_home_option
@pass_aim_context
def init_command(aim_ctx, config_type='project', region=None, keypair_name=None, home='.'):
    """Initializes an AIM Project"""
    if config_type == 'project':
        print("\nAIM Project initialization")
        print("--------------------------\n")
        print("About to create a new AIM Project directory at {}\n".format(os.getcwd()))
        cookiecutter(os.path.dirname(__file__) + os.sep + 'aim-cookiecutter' + os.sep)
    elif config_type == 'keypair':
        # ToDo: expand this command to be able to insert a new keypair into an existing EC2.yaml file
        base_dir = home + os.sep + 'Resources' + os.sep
        if os.path.isfile(base_dir + os.sep + 'EC2.yaml') or os.path.isfile(base_dir + os.sep + 'EC2.yml'):
            print("\n{}Resources/EC2.yaml file already exists. Exiting.".format(base_dir))
            sys.exit()
        init_aim_home_option(aim_ctx, home)
        print("\nAIM EC2 keypair initialization")
        print("------------------------------\n")
        ec2_file = base_dir + os.sep + 'EC2.yaml'
        with open(ec2_file, 'w') as f:
            f.write(
"""keypairs:
  {}:
    name: "{}"
    region: "{}"
""".format(
                keypair_name, keypair_name, region
            ))
        print("Added keypair {} for region {} to file at {}.".format(
            keypair_name, region, ec2_file
        ))

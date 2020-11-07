from paco.commands.helpers import (
    paco_home_option, pass_paco_context, handle_exceptions, cloud_options, init_cloud_command,
    cloud_args,
)
import click
import json
import json.decoder
import sys


@click.group(name="lambda")
@pass_paco_context
def lambda_group(paco_ctx):
    command = 'lambda'

lambda_group.help = """
Manage Lambda function(s).

"""

@lambda_group.command(name="deploy")
@cloud_args
@cloud_options
@paco_home_option
@click.pass_context
@handle_exceptions
def lambda_deploy(
    ctx,
    verbose,
    nocache,
    yes,
    warn,
    disable_validation,
    quiet_changes_only,
    config_scope,
    home='.',
):
    """
    Deploy Lambda code to AWS.
    """
    paco_ctx = ctx.obj
    command = 'lambda deploy'
    controller_type, obj = init_cloud_command(
        command,
        paco_ctx,
        verbose,
        nocache,
        yes,
        warn,
        disable_validation,
        quiet_changes_only,
        config_scope,
        home
    )
    controller = paco_ctx.get_controller(controller_type, command, obj)
    controller.lambda_deploy_command(obj)


@lambda_group.command(name="invoke")
@cloud_args
@cloud_options
@paco_home_option
@click.pass_context
@handle_exceptions
@click.option(
    '-e', '--event',
    default='',
    help='Event payload sent to Lambda when it is invoked. Must be valid JSON.'
)
@click.option(
    '-f', '--event-file',
    default='',
    help='Path to a file that will be sent as the Event payload. Must be valid JSON.'
)
def lambda_invoke(
    ctx,
    verbose,
    nocache,
    yes,
    warn,
    disable_validation,
    quiet_changes_only,
    config_scope,
    home='.',
    event='',
    event_file='',
):
    """
    Invoke a provisioned Lambda
    """
    paco_ctx = ctx.obj
    command = 'lambda invoke'

    if event_file != '' and event != '':
        print("Can not supply both -e,--event and -f,--event-file options. Event must be one or the other.")
        sys.exit()

    if event_file != '':
        try:
            with open(event_file, 'r') as fh:
                event = fh.read()
        except FileNotFoundError:
            print(f"No file exists at the location supplied with the -f,--event-file option:\n\n  {event_file}\n")
            sys.exit()

    if event != '':
        # validate the JSON
        try:
            json.loads(event)
        except json.decoder.JSONDecodeError:
            print("Event supplied is not in valid JSON format.")
            sys.exit()
    else:
        event = None

    controller_type, obj = init_cloud_command(
        command,
        paco_ctx,
        verbose,
        nocache,
        yes,
        warn,
        disable_validation,
        quiet_changes_only,
        config_scope,
        home
    )
    controller = paco_ctx.get_controller(controller_type, command, obj)
    controller.lambda_invoke_command(obj, event)

import click
from aim.cli import pass_context

from aim.api.api_network_environments import APICommands as NetworkEnvironmentAPI
from aim.api.api_network_environments import NetworkEnvironments

@click.command('api', short_help='Processes API calls from the API SQS Queue.')
@click.argument('api_command', required=True, type=click.STRING)
@click.argument('api_json', required=False, type=click.STRING)
@pass_context
def cli(aim_ctx, api_command, api_json=None):
    """Processes API calls from the API SQS Queue."""

    if api_command == None:
        return

    #aim_ctx.log('Processing API command: ' + api_command)

    api_obj = None
    if api_command in NetworkEnvironmentAPI.__members__:
        api_obj = NetworkEnvironments(aim_ctx, api_command, api_json)
    else:
        raise StackException(AimErrorCode.Unknown)

    api_obj.process()

    # 1. Pull API from Queue
    # 2. Call API method

    # Actions of an API Call
    #
    # 1. Authentication
    # 2. Get Configuration
    # 3. Change Configuration
    # 4. Apply Configuration Change


    # Configuration API
    #  - DescribeNetworkEnvironments
    #  - CreateNetworkEnvironment
    #
    # Network Environment API
    #  - Create Network Environment
    #  - Modify
    #     - Environment General SEtings
    #       - CIDR, Internet Gateway, AZs, NAT
    #       - AWS Settings (Account, Region)
    #     - Network Segments
    #       - Create/Modify/Delete
    #       - Name, AZ CIDRs, Internet Facing
    #       - Static Routes
    #       - NACLs
    #     - Connectivity
    #       - VPN
    #         - Connections
    #       - VPC Peering
    #     - Storage
    #     - Application Engine
    #       - Network
    #       - Compute
    #       - Load Balancer
    #       - Storage
    #       - Deployment

    # Configuration Change Flow
    #
    # 1.
    # 2.

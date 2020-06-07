import os.path
from paco.models import vocabulary

def get_project_context(paco_ctx):
    return {
        'project_name': os.path.basename(str(paco_ctx.home)),
        'project_title': None,
        'domain_name': None,
        'admin_username': None,
        'admin_email': None,
        'admin_ssh_public_key': None,
        'dev_account': 'devstage',
        'staging_account': 'devstage',
        'prod_account': 'prod',
        'tools_account': 'tools',
        'network_environment_name': None,
        'network_environment_title': None,
        'application_name': None,
        'application_title': None,
        'aws_default_region': 'us-east-1',
        'aws_default_region_allowed_values': vocabulary.aws_regions.keys(),
        'master_account_id': None,
        'master_root_email': None,
    }

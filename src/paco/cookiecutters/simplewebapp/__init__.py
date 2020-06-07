import os.path
from paco.models import vocabulary

def get_project_context(paco_ctx):
    return {
        'project_name': os.path.basename(str(paco_ctx.home)),
        'project_title': None,
        'network_environment_name': None,
        'network_environment_title': None,
        'application_name': None,
        'application_title': None,
        'aws_default_region': None,
        'aws_default_region_allowed_values': vocabulary.aws_regions.keys(),
        'master_account_id': None,
        'master_root_email': None,
    }

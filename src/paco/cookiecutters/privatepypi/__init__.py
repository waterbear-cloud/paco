import os.path
from paco.models import vocabulary

def get_project_context(paco_ctx):
    return {
        'project_name': os.path.basename(str(paco_ctx.home)),
        'budget': 'Y',
        'budget_allowed_values': ['Y','y','yes','N','n','no'],
        'project_title': 'My Paco Project',
        'network_environment_name': 'mynet',
        'network_environment_title': 'My Network',
        'aws_default_region': 'us-east-1',
        'aws_default_region_allowed_values': vocabulary.aws_regions.keys(),
        'master_account_id': None,
        'master_root_email': None,
    }

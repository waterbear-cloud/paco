from paco.models import schemas
from paco.models.base import most_specialized_interfaces
from zope.interface import Interface
import zope.schema
import zope.schema.interfaces


def auto_export_obj_to_dict(obj):
    export_dict = {}
    for interface in most_specialized_interfaces(obj):
        fields = zope.schema.getFields(interface)
        for name, field in fields.items():
            export_dict[name] = getattr(obj, name, None)
    return export_dict

def export_fields_to_dict(obj, fields=None, parentname=None):
    export_dict = {'name': obj.name, 'title': obj.title, 'ref': obj.paco_ref_parts}
    if schemas.IDeployable.providedBy(obj):
        export_dict['enabled'] = obj.is_enabled()
    if fields != None:
        for fieldname in fields:
            value = getattr(obj, fieldname, None)
            if value == None:
                continue
            if Interface.providedBy(value):
                if not isinstance(value, (str, int, float, list)):
                    value = auto_export_obj_to_dict(value)
            export_dict[fieldname] = value
    if parentname != None:
        export_dict[parentname] = obj.__parent__.name
    return export_dict

def mapping_to_key_list(obj):
    return [key for key in obj.keys()]

def display_project_as_json(project):
    json_docs = {
        'project': [],
        'account': [],
        'netenv': [],
        'env': [],
        'env_regions': [],
        'networks': [],
        'backupvaults': [],
        'secretsmanagers': [],
        'applications': [],
        'resourcegroups': [],
        'resources': [],
        'globalresources': [],
        'iamusers': [],
        'cloudtrails': [],
        'codecommits': [],
        'iamuserpermissions': [],
    }
    json_docs['project'].append(
        export_fields_to_dict(
            project,
            fields=['paco_project_version','active_regions', 's3bucket_hash'],
        )
    )
    for account in project['accounts'].values():
        account_dict = export_fields_to_dict(account, fields=['account_id', 'region'])
        json_docs['account'].append(account_dict)
    for name in project['resource'].keys():
        json_docs['globalresources'].append({'name': name})
    if 'cloudtrail' in project['resource']:
        for trail in project['resource']['cloudtrail'].trails.values():
            ct_dict = export_fields_to_dict(trail, fields=['s3_bucket_account','s3_key_prefix'])
            json_docs['cloudtrails'].append(ct_dict)
    if 'codecommit' in project['resource']:
        for repo in project['resource']['codecommit'].repo_list():
            repo_dict = export_fields_to_dict(repo, fields=[
                'description','account','region'
            ])
            repo_dict['usernames'] = [user.name for user in repo.users.values()]
            json_docs['codecommits'].append(repo_dict)
    if 'iam' in project['resource']:
        for user in project['resource']['iam'].users.values():
            user_dict = export_fields_to_dict(user, fields=[
                'username','description','account_whitelist','console_access_enabled','programmatic_access',
            ])
            json_docs['iamusers'].append(user_dict)
            for perm in user.permissions.values():
                perm_dict = export_fields_to_dict(perm, fields=[
                    'type','accounts','read_only','managed_policies',
                ])
                perm_dict['iamuser_name'] = user.name
                json_docs['iamuserpermissions'].append(perm_dict)
    for netenv in project['netenv'].values():
        netenv_dict = export_fields_to_dict(netenv)
        # netenv_dict['environments'] = mapping_to_key_list(netenv)
        json_docs['netenv'].append(netenv_dict)
        for env in netenv.values():
            env_dict = export_fields_to_dict(env, parentname='netenv')
            json_docs['env'].append(env_dict)
            for env_region in env.values():
                network = env_region.network
                backup_vaults = env_region.backup_vaults
                secrets_manager = env_region.secrets_manager

                if env_region.name == 'default':
                    continue
                env_region_dict = export_fields_to_dict(env_region)
                env_region_dict['account_ref'] = network.aws_account.split(' ')[1]
                json_docs['env_regions'].append(env_region_dict)

                # Network
                network_dict = export_fields_to_dict(network, fields=['availability_zones'])
                network_dict['account_ref'] = network.aws_account.split(' ')[1]
                json_docs['networks'].append(network_dict)

                # Backup Vaults
                backup_dict = export_fields_to_dict(backup_vaults, fields=[])
                backup_dict['vaults'] = [vault.name for vault in backup_vaults.values()]
                json_docs['backupvaults'].append(backup_dict)

                # Secrets Manager
                for sm_app in secrets_manager.values():
                    secrets_manager_dict = export_fields_to_dict(sm_app, fields=[])
                    secrets_manager_dict['managers'] = []
                    json_docs['secretsmanagers'].append(secrets_manager_dict)

                for app in env_region.applications.values():
                    app_dict = export_fields_to_dict(app)
                    json_docs['applications'].append(app_dict)
                    for resource_group in app.groups.values():
                        resource_group_dict = export_fields_to_dict(resource_group)
                        json_docs['resourcegroups'].append(resource_group_dict)
                        for resource in resource_group.resources.values():
                            resource_dict = export_fields_to_dict(resource, fields=['type', 'order', 'change_protected'])
                            json_docs['resources'].append(resource_dict)

    return json_docs

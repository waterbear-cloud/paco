from paco.models import schemas
from paco.models.base import most_specialized_interfaces, get_all_fields
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
            if value == None or value == '':
                continue
            if Interface.providedBy(value):
                if not isinstance(value, (str, int, float, list)):
                    value = auto_export_obj_to_dict(value)
            export_dict[fieldname] = value
    if parentname != None:
        export_dict[parentname] = obj.__parent__.name
    return export_dict

def autoexport_fields_to_dict(obj):
    export_dict = {}
    export_dict['ref'] = obj.paco_ref_parts
    for fieldname in get_all_fields(obj).keys():
        if fieldname in ('enabled'):
            continue
        value = getattr(obj, fieldname, None)
        if value == None or value == '' or value == [] or value == {}:
            continue
        export_dict[fieldname] = value
    if schemas.IDeployable.providedBy(obj):
        export_dict['enabled'] = obj.is_enabled()
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
        'notifications': [],
        'resourcegroups': [],
        'resources': [],
        'globalresources': [],
        'iamusers': [],
        'cloudtrails': [],
        'codecommits': [],
        'iamuserpermissions': [],
        'cloudwatchalarms': [],
        'logsources': [],
        'healthchecks': [],
        'services': [],
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
    for service in project['service'].values():
        json_docs['services'].append({
            'ref': service.paco_ref_parts,
            'name': service.name,
            'version': getattr(service, 'version', None)
        })

    for log_set in project.monitor.cw_logging.log_sets.values():
        for log_group in log_set.log_groups.values():
            for source in log_group.sources.values():
                log_source_dict = export_fields_to_dict(
                    source,
                    fields=['path', 'log_stream_name']
                )
                log_source_dict['log_set_name'] = log_set.name
                log_source_dict['log_set_title'] = log_set.title
                log_source_dict['log_group_name'] = log_group.name
                metric_filters = []
                for mf in log_group.metric_filters.values():
                    mts = []
                    for mt in mf.metric_transformations:
                        mts.append({'metric_name': mt.metric_name, 'metric_value': mt.metric_value})
                    metric_filters.append({'filter_pattern': mf.filter_pattern, 'metric_transformations': mts})
                if len(metric_filters) > 0:
                    log_source_dict['metric_filters'] = metric_filters
                json_docs['logsources'].append(log_source_dict)
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
                    # App Alarms
                    add_alarms(app.monitoring, json_docs['cloudwatchalarms'], 'app')
                    for notif in app.notifications.values():
                        notif_dict = autoexport_fields_to_dict(notif)
                        json_docs['notifications'].append(notif_dict)
                    if app.monitoring != None and app.monitoring.health_checks != None:
                        for check in app.monitoring.health_checks.values():
                            if check.is_enabled():
                                check_dict = autoexport_fields_to_dict(check)
                                json_docs['healthchecks'].append(check_dict)
                    for resource_group in app.groups.values():
                        resource_group_dict = export_fields_to_dict(resource_group)
                        json_docs['resourcegroups'].append(resource_group_dict)
                        for resource in resource_group.resources.values():
                            resource_dict = export_fields_to_dict(resource, fields=['type', 'order', 'change_protected'])
                            json_docs['resources'].append(resource_dict)
                            # Resource Alarms
                            if hasattr(resource, 'monitoring'):
                                add_alarms(resource.monitoring, json_docs['cloudwatchalarms'], 'resource')

    return json_docs

def add_alarms(monitoring, alarms, alarm_context):
    if monitoring == None:
        return
    for alarm_set in monitoring.alarm_sets.values():
        for alarm in alarm_set.values():
            if not alarm.is_enabled():
                continue
            alarm_dict = export_fields_to_dict(
                alarm,
                fields=[
                    'description', 'classification', 'severity', 'log_set_name', 'log_group_name', 'metric_name',
                    'threshold', 'comparison_operator', 'statistic', 'period',
                    'evaluation_periods', 'treat_missing_data', 'runbook_url'
                ]
            )
            alarm_dict['alarm_context'] = alarm_context
            alarm_dict['alarm_set_name'] = alarm_set.name
            dimensions = []
            for dimension in alarm.dimensions:
                dimensions.append({'name': dimension.name, 'value': dimension.value})
            alarm_dict['dimensions'] = dimensions
            alarms.append(alarm_dict)

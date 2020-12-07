from paco.models import schemas
from paco.models.base import most_specialized_interfaces, get_all_fields
from paco.models.loader import RESOURCES_CLASS_MAP
from zope.interface import Interface
from zope.schema import Field
import inspect
import zope.schema
import zope.schema.interfaces
import zope.interface.common.mapping
import zope.interface.interface


def full_recursive_export(obj):
    "Export all fields, include sub-fields"
    export_dict = {}
    for fieldname, field in get_all_fields(obj).items():
        # if fieldname == 'enabled': continue
        value = getattr(obj, fieldname, None)
        # List
        if zope.schema.interfaces.IList.providedBy(field):
            export_dict[fieldname] = []
            for item in value:
                if zope.schema.interfaces.IObject.providedBy(field.value_type):
                    item_export = full_recursive_export(item)
                else:
                    item_export = item
                export_dict[fieldname].append(item_export)
        # Mapping
        elif zope.interface.common.mapping.IMapping.providedBy(value):
            export_dict[fieldname] = {}
            for name, childvalue in value.items():
                export_dict[fieldname][name] = full_recursive_export(childvalue)
        # Object
        elif zope.schema.interfaces.IObject.providedBy(field):
            export_dict[fieldname] = full_recursive_export(value)
        # Simple value: String, Float, Int, Ref
        else:
            export_dict[fieldname] = getattr(obj, fieldname, None)
    return export_dict

def auto_export_obj_to_dict(obj):
    export_dict = {}
    for interface in most_specialized_interfaces(obj):
        fields = zope.schema.getFields(interface)
        for name, field in fields.items():
            export_dict[name] = getattr(obj, name, None)
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

def recursive_resource_export(obj):
    export_dict = full_recursive_export(obj)
    export_dict['ref'] = obj.paco_ref_parts
    if schemas.IDeployable.providedBy(obj):
        export_dict['enabled'] = obj.is_enabled()
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

def mapping_to_key_list(obj):
    return [key for key in obj.keys()]

resource_type_entity_map = {
    'ASG': 'asgs',
    'DeploymentPipeline': 'deploymentpipelines',
    'ECRRepository': 'ecrrepositories',
    'ECSServices': 'ecsservices',
    'LBApplication': 'lbapplications',
    'S3Bucket': 's3buckets'
}

"""
    'ACM': ACM,
    'ApiGatewayRestApi': ApiGatewayRestApi,
    'ASG': ASG,
    'DBParameterGroup': DBParameterGroup,
    'DBClusterParameterGroup': DBClusterParameterGroup,
    'DeploymentPipeline': DeploymentPipeline,
    'EC2': EC2,
    'CloudFront': CloudFront,
    'CodeDeployApplication': CodeDeployApplication,
    'CognitoIdentityPool': CognitoIdentityPool,
    'CognitoUserPool': CognitoUserPool,
    'Dashboard': CloudWatchDashboard,
    'EBS': EBS,
    'EBSVolumeMount': EBSVolumeMount,
    'ECSCluster': ECSCluster,
    'ECSServices': ECSServices,
    'ECRRepository': ECRRepository,
    'EIP': EIP,
    'EFS': EFS,
    'ElastiCacheRedis': ElastiCacheRedis,
    'ElasticsearchDomain': ElasticsearchDomain,
    'EventsRule': EventsRule,
    'IAMUser': IAMUserResource,
    'IoTPolicy': IoTPolicy,
    'IoTTopicRule': IoTTopicRule,
    'IoTAnalyticsPipeline': IoTAnalyticsPipeline,
    'Lambda': Lambda,
    'LBApplication': LBApplication,
    'ManagedPolicy': ManagedPolicy,
    'PinpointApplication': PinpointApplication,
    'RDS': RDS,
    'RDSMysql': RDSMysql,
    'RDSMysqlAurora': RDSMysqlAurora,
    'RDSPostgresql': RDSPostgresql,
    'RDSPostgresqlAurora': RDSPostgresqlAurora,
    'Route53HealthCheck': Route53HealthCheck,
    'S3Bucket': ApplicationS3Bucket,
    'SNSTopic': SNSTopic,
"""

def display_project_as_json(project):
    json_docs = {
        'project': [],
        'fieldhelp': [],
        'account': [],
        'netenv': [],
        'env': [],
        'env_regions': [],
        'networks': [],
        'backupvaults': [],
        'secretsmanagerapps': [],
        'secretsmanagergroups': [],
        'secretsmanagersecrets': [],
        'applications': [],
        'notifications': [],
        'resourcegroups': [],
        'resources': [],
        'globalresources': [],
        'iam': [],
        'cloudtrail': [],
        'codecommit': [],
        'sns': [],
        'snsdefaultlocations': [],
        'iamuserpermissions': [],
        'cloudwatchalarms': [],
        'cloudwatchlogs': [],
        'logsources': [],
        'healthchecks': [],
        'services': [],
    }
    for entity_name in RESOURCES_CLASS_MAP.keys():
        json_docs[entity_name.lower()] = []
    project_dict = export_fields_to_dict(
        project,
        fields=['paco_project_version','active_regions', 's3bucket_hash'],
    )
    project_dict['ref'] = 'project'
    json_docs['project'].append(project_dict)

    # Help - export from schemas
    for name, obj in inspect.getmembers(schemas):
        if isinstance(obj, zope.interface.interface.InterfaceClass):
            for iface_name in list(obj):
                if obj[iface_name].interface.__name__ == name:
                    if isinstance(obj[iface_name], Field):
                        # strip the leading I from the interface name, e.g.
                        #   ICloudTrail becomes CloudTrail
                        # keys would be in the form:
                        #   CloudTrail.is_multi_region_trail
                        key = f"{name[1:]}.{obj[iface_name].__name__}"
                        helpfields_dict = {
                            'id': key,
                            'help': obj[iface_name].title,
                        }
                        json_docs['fieldhelp'].append(helpfields_dict)

    for account in project['accounts'].values():
        account_dict = recursive_resource_export(account) # export_fields_to_dict(account, fields=['account_id', 'region'])
        json_docs['account'].append(account_dict)
    for name in project['resource'].keys():
        json_docs['globalresources'].append({'name': name})
    if 'cloudtrail' in project['resource']:
        for trail in project['resource']['cloudtrail'].trails.values():
            ct_dict = recursive_resource_export(trail)
            json_docs['cloudtrail'].append(ct_dict)
    if 'codecommit' in project['resource']:
        for repo in project['resource']['codecommit'].repo_list():
            repo_dict = export_fields_to_dict(repo, fields=[
                'description','account','region'
            ])
            repo_dict['usernames'] = [user.name for user in repo.users.values()]
            json_docs['codecommit'].append(repo_dict)
    if 'sns' in project['resource']:
        sns = project['resource']['sns']
        index = 0
        for location in sns.default_locations:
            location_dict = recursive_resource_export(location)
            location_dict['ref'] = f"resource.sns.default_locations.{index}"
            index += 1
            json_docs['snsdefaultlocations'].append(location_dict)
        for sns in sns.topics.values():
            sns_dict = recursive_resource_export(sns)
            json_docs['sns'].append(sns_dict)
    # legacy 'snstopics' which are exported as if they were 'sns' for simplicity
    if 'snstopics' in project['resource']:
        snstopics = project['resource']['snstopics']
        regions = snstopics.regions
        if snstopics.regions == ['ALL']:
            regions = project.active_regions
        for region in regions:
            for snstopic in project['resource']['snstopics'][region].values():
                sns_dict = recursive_resource_export(snstopic)
                sns_dict['ref'] = f"resource.sns.topics.{snstopic.name}"
                sns_dict['locations'] = [{'account': snstopics.account, 'regions': regions}]
                json_docs['sns'].append(sns_dict)
    if 'iam' in project['resource']:
        for user in project['resource']['iam'].users.values():
            user_dict = recursive_resource_export(user)
            user_dict['programmatic_access']['enabled'] = user.programmatic_access.enabled
            json_docs['iam'].append(user_dict)
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
                network_dict = recursive_resource_export(network)
                network_dict['account_ref'] = network.aws_account.split(' ')[1]
                if network.vpc.private_hosted_zone != None and network.vpc.private_hosted_zone.enabled == True:
                    network_dict['vpc']['private_dns_name'] = network.vpc.private_hosted_zone.name
                security_groups_dict = {}
                for key1 in network.vpc.security_groups.keys():
                    security_groups_dict[key1] = {}
                    for key2 in network.vpc.security_groups[key1].keys():
                        security_groups_dict[key1][key2] = recursive_resource_export(network.vpc.security_groups[key1][key2])
                network_dict['vpc']['security_groups'] = security_groups_dict
                json_docs['networks'].append(network_dict)

                # Backup Vaults
                for backup_vault in backup_vaults.values():
                    backup_dict = recursive_resource_export(backup_vault)
                    json_docs['backupvaults'].append(backup_dict)

                # Secrets Manager
                #   - SM Application -> secretsmanagerapps
                #     - SM Group -> secretsmanagergroups
                #       - SM Secret -> secretsmanagersecrets
                for sm_app in secrets_manager.values():
                    sm_app_dict = export_fields_to_dict(sm_app, fields=[])
                    json_docs['secretsmanagerapps'].append(sm_app_dict)
                    for sm_group in sm_app.values():
                        sm_group_dict = export_fields_to_dict(sm_group, fields=[])
                        json_docs['secretsmanagergroups'].append(sm_group_dict)
                        for secret in sm_group.values():
                            secret_dict = recursive_resource_export(secret)
                            json_docs['secretsmanagersecrets'].append(secret_dict)

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
                        resource_group_dict = export_fields_to_dict(resource_group, fields=['type'])
                        json_docs['resourcegroups'].append(resource_group_dict)
                        for resource in resource_group.resources.values():
                            resource_dict = export_fields_to_dict(resource, fields=['type', 'order', 'change_protected'])
                            json_docs['resources'].append(resource_dict)
                            # details export
                            entity_name = resource.type.lower()
                            full_resource_dict = recursive_resource_export(resource)
                            if resource.type == 'S3Bucket':
                                full_resource_dict['awsBucketName'] = resource.get_bucket_name()
                            json_docs[entity_name].append(full_resource_dict)

                            # Resource Alarms
                            if hasattr(resource, 'monitoring'):
                                add_alarms(resource.monitoring, json_docs['cloudwatchalarms'], 'resource')
                                add_logs(resource.monitoring, json_docs['cloudwatchlogs'], 'resource')

    return json_docs

def add_logs(monitoring, logs, log_context):
    if monitoring == None:
        return
    if not monitoring.is_enabled():
        return
    for log_set in monitoring.log_sets.values():
        for log_group in log_set.log_groups.values():
            log_group_dict = recursive_resource_export(log_group)
            log_group_dict['log_set_name'] = log_set.name
            logs.append(log_group_dict)

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

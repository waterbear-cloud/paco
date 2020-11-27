from paco import utils
from paco.cftemplates.cftemplates import StackTemplate
import troposphere
import troposphere.backup

# Troposphere monkey-patch for CopyActions
# (remove once PR for this is merged and released)

from troposphere import AWSProperty
basestring = str

class CopyActionResourceType(AWSProperty):
    props = {
        'DestinationBackupVaultArn': (basestring, True),
        'Lifecycle': (troposphere.backup.LifecycleResourceType, False),
    }

troposphere.backup.CopyActionResourceType = CopyActionResourceType
troposphere.backup.BackupRuleResourceType.props['CopyActions'] = ([CopyActionResourceType], False)

class BackupVault(StackTemplate):
    def __init__(self, stack, paco_ctx, role):
        vault = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name(vault.name)
        self.init_template('Backup Vault: ' + vault.name)
        self.paco_ctx.log_action_col("Init", "Backup", "Vault")
        if not vault.is_enabled():
            return

        # Service Role ARN parameter
        service_role_arn_param = None
        if role != None:
            service_role_arn_param = self.create_cfn_parameter(
                param_type='String',
                name='ServiceRoleArn',
                description='The Backup service Role to assume',
                value=role.get_arn()
            )

        # BackupVault resource
        cfn_export_dict = {}
        cfn_export_dict['BackupVaultName'] = vault.name

        # BackupVault Notifications
        if vault.notification_events:
            notification_paco_ref = self.paco_ctx.project['resource']['sns'].computed[self.account_ctx.name][stack.aws_region][vault.notification_group].paco_ref + '.arn'
            param_name = 'Notification{}'.format(utils.md5sum(str_data=notification_paco_ref))
            notification_param = self.create_cfn_parameter(
                param_type='String',
                name=param_name,
                description='SNS Topic to notify',
                value=notification_paco_ref,
                min_length=1, # prevent borked empty values from breaking notification
            )
            cfn_export_dict['Notifications'] = {
                'BackupVaultEvents': vault.notification_events,
                'SNSTopicArn': troposphere.Ref(notification_param)
            }

        vault_logical_id = 'BackupVault'
        vault_resource = troposphere.backup.BackupVault.from_dict(
            vault_logical_id,
            cfn_export_dict
        )
        self.template.add_resource(vault_resource)

        # BackupVault Outputs
        self.create_output(
            title='BackupVaultName',
            value=troposphere.GetAtt(vault_resource, 'BackupVaultName'),
            ref=vault.paco_ref_parts + '.name',
        )
        self.create_output(
            title='BackupVaultArn',
            value=troposphere.GetAtt(vault_resource, 'BackupVaultArn'),
            ref=vault.paco_ref_parts + '.arn'
        )

        # BackupPlans
        for plan in vault.plans.values():
            # PlanRules
            rules_list = []
            for rule in plan.plan_rules:
                rule_dict = {
                    'RuleName': rule.title_or_name,
                    'TargetBackupVault': vault.name
                }
                if rule.schedule_expression:
                    rule_dict['ScheduleExpression'] = rule.schedule_expression
                if rule.lifecycle_delete_after_days != None or rule.lifecycle_move_to_cold_storage_after_days != None:
                    lifecycle_dict = {}
                    if rule.lifecycle_delete_after_days != None:
                        lifecycle_dict['DeleteAfterDays'] =  rule.lifecycle_delete_after_days
                    if rule.lifecycle_move_to_cold_storage_after_days != None:
                        lifecycle_dict['MoveToColdStorageAfterDays'] = rule.lifecycle_move_to_cold_storage_after_days
                    rule_dict['Lifecycle'] = lifecycle_dict

                # CopyActions
                for copy_action in rule.copy_actions:
                    copy_action_dict = {
                        'DestinationBackupVaultArn': copy_action.destination_vault,
                    }
                    if 'CopyActions' not in rule_dict:
                        rule_dict['CopyActions'] = []
                    if copy_action.lifecycle_delete_after_days != None or copy_action.lifecycle_move_to_cold_storage_after_days != None:
                        copy_lifecycle_dict = {}
                        if copy_action.lifecycle_delete_after_days != None:
                            copy_lifecycle_dict['DeleteAfterDays'] =  copy_action.lifecycle_delete_after_days
                        if copy_action.lifecycle_move_to_cold_storage_after_days != None:
                            copy_lifecycle_dict['MoveToColdStorageAfterDays'] = copy_action.lifecycle_move_to_cold_storage_after_days
                        copy_action_dict['Lifecycle'] = copy_lifecycle_dict
                    rule_dict['CopyActions'].append(copy_action_dict)

                rules_list.append(rule_dict)
            cfn_export_dict = {
                'BackupPlan': {
                    'BackupPlanName': plan.name,
                    'BackupPlanRule': rules_list
                }
            }
            plan_logical_id = self.create_cfn_logical_id('BackupPlan' + plan.name)
            plan_resource = troposphere.backup.BackupPlan.from_dict(
                plan_logical_id,
                cfn_export_dict
            )
            plan_resource.DependsOn = [vault_resource.title]
            self.template.add_resource(plan_resource)

            # PlanSelection resources
            idx = 0
            for selection in plan.selections:
                cfn_export_dict = {
                    'BackupPlanId': troposphere.Ref(plan_resource),
                    'BackupSelection': {}
                }
                # Tag-based selections
                tags_list = []
                for tag in selection.tags:
                    tag_dict = {}
                    tag_dict['ConditionKey'] = tag.condition_key
                    tag_dict['ConditionType'] = tag.condition_type
                    tag_dict['ConditionValue'] = tag.condition_value
                    tags_list.append(tag_dict)
                if tags_list:
                    cfn_export_dict['BackupSelection']['ListOfTags'] = tags_list
                if selection.title:
                    cfn_export_dict['BackupSelection']['SelectionName'] = "Selection: " + selection.title

                # Resource-based selections
                if selection.resources:
                    resource_arns = []
                    for paco_ref in selection.resources:
                        from paco.models.references import get_model_obj_from_ref
                        obj = get_model_obj_from_ref(paco_ref, self.paco_ctx.project)
                        resource_arns.append(
                            obj.get_arn()
                        )
                    cfn_export_dict['BackupSelection']['Resources'] = resource_arns

                # Role
                cfn_export_dict['BackupSelection']['IamRoleArn'] = troposphere.Ref(service_role_arn_param)
                selection_logical_id = self.create_cfn_logical_id('BackupPlan{}Selection{}'.format(plan.name, idx))
                selection_resource = troposphere.backup.BackupSelection.from_dict(
                    selection_logical_id,
                    cfn_export_dict
                )
                selection_resource.DependsOn = [plan_resource.title]
                self.template.add_resource(selection_resource)
                idx += 1

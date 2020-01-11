import troposphere
import troposphere.backup

from paco import utils
from paco.cftemplates.cftemplates import CFTemplate

class BackupVault(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        vault,
        role
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            config_ref=vault.paco_ref_parts,
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name(vault.name)
        self.init_template('Backup Vault: ' + vault.name)
        self.paco_ctx.log_action_col("Init", "Backup", "Vault")
        is_enabled = vault.is_enabled()
        if not is_enabled:
            self.set_template(self.template.to_yaml())
            return

        # Service Role ARN parameter
        if role != None:
            service_role_arn_param = self.create_cfn_parameter(
                param_type='String',
                name='ServiceRoleArn',
                description='The Backup service Role to assume',
                value=role.get_arn(),
                use_troposphere=True,
                troposphere_template=self.template,
            )

        # BackupVault resource
        cfn_export_dict = {}
        cfn_export_dict['BackupVaultName'] = vault.name

        # BackupVault Notifications
        if vault.notification_events:
            notification_paco_ref = self.paco_ctx.project['resource']['notificationgroups'][aws_region][vault.notification_group].paco_ref + '.arn'
            param_name = 'Notification{}'.format(utils.md5sum(str_data=notification_paco_ref))
            notification_param = self.create_cfn_parameter(
                param_type='String',
                name=param_name,
                description='SNS Topic to notify',
                value=notification_paco_ref,
                min_length=1, # prevent borked empty values from breaking notification
                use_troposphere=True
            )
            self.template.add_parameter(notification_param)
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
        vault_name_output_logical_id = 'BackupVaultName'
        self.template.add_output(
            troposphere.Output(
                title=vault_name_output_logical_id,
                Value=troposphere.GetAtt(vault_resource, 'BackupVaultName')
            )
        )
        self.register_stack_output_config(
            vault.paco_ref_parts + '.name',
            vault_name_output_logical_id
        )

        vault_arn_output_logical_id = 'BackupVaultArn'
        self.template.add_output(
            troposphere.Output(
                title=vault_arn_output_logical_id,
                Value=troposphere.GetAtt(vault_resource, 'BackupVaultArn')
            )
        )
        self.register_stack_output_config(
            vault.paco_ref_parts + '.arn',
            vault_arn_output_logical_id
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
                        lifecycle_dict['MoveToColdStorageAfterDays'] = reul.lifecycle_move_to_cold_storage_after_days
                    rule_dict['Lifecycle'] = lifecycle_dict
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
                    cfn_export_dict['BackupSelection']['SelectionName'] = selection.title

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
                selection_logical_id = self.create_cfn_logical_id('Plan{}Selection{}'.format(plan.name, idx))
                selection_resource = troposphere.backup.BackupSelection.from_dict(
                    selection_logical_id,
                    cfn_export_dict
                )
                selection_resource.DependsOn = [plan_resource.title]
                self.template.add_resource(selection_resource)
                idx += 1

        self.enabled = is_enabled
        self.set_template(self.template.to_yaml())

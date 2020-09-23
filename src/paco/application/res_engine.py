"""
ResourceEngines initialize a Resource for an Application
"""
from paco.models import schemas
import paco.cftemplates

class ResourceEngine():
    "Base class for ResourceEngines"

    def __init__(self, app_engine, grp_id, res_id, resource, stack_tags):
        "Save the ApplicationEngine object and make it's attributes available as ResourceEngine attributes for convenience"
        self.app_engine = app_engine
        self.app = app_engine.app
        self.grp_id = grp_id
        self.res_id = res_id
        self.resource = resource
        self.stack_tags = stack_tags
        self.paco_ctx = self.app_engine.paco_ctx
        self.aws_region = self.app_engine.aws_region
        self.stack_group = self.app_engine.stack_group
        self.account_ctx = self.app_engine.account_ctx
        if self.app_engine.env_ctx != None:
            self.env_ctx = self.app_engine.env_ctx
            self.env = self.env_ctx.env_region
        self.app_id = self.app_engine.app.name
        self.gen_iam_role_id = self.app_engine.gen_iam_role_id

    def init_resource(self):
        "Initialize the Resource"
        raise NotImplementedError

    def log_init_status(self):
        "Logs the initialization status of a resource"
        self.paco_ctx.log_action_col(
            'Init', 'Application', 'Resource',
            self.resource.title_or_name + ': '+ self.resource.name,
            enabled = self.resource.is_enabled()
        )

    def init_monitoring(self):
        "Add an Alarms template with Alarms specific to the Resource"
        # If alarm_sets exist init alarms for them
        if schemas.IRDSAurora.providedBy(self.resource):
            # RDS Aurora can have alarms for each individual DB Instance
            for db_instance in self.resource.db_instances.values():
                monitoring = getattr(db_instance, 'monitoring', None)
                # if no instance-level monitoring use default_instance monitoring
                if monitoring == None:
                    monitoring = getattr(self.resource.default_instance, 'monitoring', None)
                    db_instance.monitoring = monitoring
                if monitoring != None and monitoring.enabled and \
                    getattr(monitoring, 'alarm_sets', None) != None and \
                    len(monitoring.alarm_sets.values()) > 0:
                    self.stack_group.add_new_stack(
                        self.aws_region,
                        db_instance,
                        paco.cftemplates.CWAlarms,
                        change_protected=False,
                        support_resource_ref_ext=f'db_instances.{db_instance.name}.alarms',
                        stack_tags=self.stack_tags
                    )
        elif schemas.IECSServices.providedBy(self.resource):
            # ToDo: validate that there is at least one AlarmSets in the services
            # (or use a fall-back default)
            if getattr(self.resource, 'monitoring', None) != None and \
            self.resource.monitoring.enabled == True:
                self.stack_group.add_new_stack(
                    self.aws_region,
                    self.resource,
                    paco.cftemplates.CWAlarms,
                    change_protected=False,
                    support_resource_ref_ext='alarms',
                    stack_tags=self.stack_tags
                )
        elif getattr(self.resource, 'monitoring', None) != None and \
            self.resource.monitoring.enabled and \
            getattr(self.resource.monitoring, 'alarm_sets', None) != None and \
            len(self.resource.monitoring.alarm_sets.values()) > 0:
            self.stack_group.add_new_stack(
                self.aws_region,
                self.resource,
                paco.cftemplates.CWAlarms,
                change_protected=False,
                support_resource_ref_ext='alarms',
                stack_tags=self.stack_tags
            )


from paco.stack_grps.grp_route53 import Route53StackGroup
from paco.stack import StackGroup, StackOrder
from paco.cftemplates import Route53RecordSet
from paco.core.exception import StackException, PacoException
from paco.core.exception import PacoErrorCode
from paco.controllers.controllers import Controller
from paco.models import schemas
from paco.models.references import is_ref, get_model_obj_from_ref
import os


class Route53RecordSetStackGroup(StackGroup):
    def __init__(self, paco_ctx, account_ctx, controller):
        aws_name = account_ctx.get_name()
        super().__init__(
            paco_ctx,
            account_ctx,
            'Route53',
            aws_name,
            controller
        )
        # Initialize config with a deepcopy of the project defaults
        self.account_ctx = account_ctx
        self.stack_list = []

class Route53Controller(Controller):
    def __init__(self, paco_ctx):
        if paco_ctx.legacy_flag('route53_controller_type_2019_09_18') == True:
            controller_type = 'Service'
        else:
            controller_type = 'Resource'
        super().__init__(
            paco_ctx,
            controller_type,
            "Route53"
        )
        if not 'route53' in self.paco_ctx.project['resource'].keys():
            self.init_done = True
            return
        self.config = self.paco_ctx.project['resource']['route53']
        if self.config != None:
            self.config.resolve_ref_obj = self
        self.stack_grps = []
        self.second = False
        self.init_done = False

    def init(self, command=None, model_obj=None):
        if self.init_done:
            return
        self.config.resolve_ref_obj = self
        self.init_done = True
        self.paco_ctx.log_start('Init', self.config)
        self.init_stack_groups()
        self.paco_ctx.log_finish('Init', self.config)

    def init_stack_groups(self):
        # TODO: Fixed above now with init done flag?
        if self.second == True:
            raise StackException(PacoErrorCode.Unknown)
        self.second = True
        for account_name in self.config.get_hosted_zones_account_names():
            account_ctx = self.paco_ctx.get_account_context(account_name=account_name)
            route53_stack_grp = Route53StackGroup(
                self.paco_ctx,
                account_ctx,
                self.config,
                self
            )
            self.stack_grps.append(route53_stack_grp)

    def add_record_set(
        self,
        account_ctx,
        region,
        resource,
        dns,
        record_set_type,
        enabled=True,
        resource_records=None,
        alias_dns_name=None,
        alias_hosted_zone_id=None,
        stack_group=None,
        async_stack_provision=False,
        config_ref=None
    ):
        record_set_config = {
            'enabled' : enabled,
            'dns': dns,
            'alias_dns_name': alias_dns_name,
            'alias_hosted_zone_id': alias_hosted_zone_id,
            'record_set_type': record_set_type,
            'resource_records': resource_records
        }
        if stack_group == None:
            # I don't believe this case happens anymore, and it doesn't
            # look like it does anything.
            raise PacoException(PacoErrorCode.Unknown)
            #record_set_stack_group = Route53RecordSetStackGroup(
            #    self.paco_ctx, account_ctx, self
            #)
            #record_set_stack_group.add_new_stack(
            #    region,
            #    resource,
            #    Route53RecordSet,
            #    extra_context={'record_set_config': record_set_config, 'record_set_name': dns.domain_name}
            #)
        else:
            stack_account_ctx = account_ctx
            if is_ref(dns.hosted_zone):
                hosted_zone_obj = get_model_obj_from_ref(dns.hosted_zone, self.paco_ctx.project)
                stack_account_ctx = self.paco_ctx.get_account_context(account_ref=hosted_zone_obj.account)
            stack_orders = None
            if async_stack_provision == True:
                stack_orders = [StackOrder.PROVISION, StackOrder.WAITLAST]
            stack_group.add_new_stack(
                region,
                resource,
                Route53RecordSet,
                account_ctx=stack_account_ctx,
                stack_orders=stack_orders,
                extra_context={'record_set_config': record_set_config, 'record_set_name': dns.domain_name}
            )

    def validate(self):
        for stack_grp in self.stack_grps:
            stack_grp.validate()

    def provision(self):
        for stack_grp in self.stack_grps:
            stack_grp.provision()

    def delete(self):
        for stack_grp in reversed(self.stack_grps):
            stack_grp.delete()

    def get_stack(self, zone_id):
        for stack_grp in self.stack_grps:
            if stack_grp.has_zone_id(zone_id):
                return stack_grp.get_stack(zone_id)
        return None

    def resolve_ref(self, ref):
        # route53.example.id
        if ref.last_part == "id":
            hosted_zone = self.get_stack(zone_id=ref.parts[2]).resource
            # legacy support
            if schemas.IRoute53Resource.providedBy(hosted_zone):
                hosted_zone = hosted_zone.hosted_zones[ref.parts[2]]
            if hosted_zone.external_resource != None:
                return hosted_zone.external_resource.hosted_zone_id
            else:
                return self.get_stack(zone_id=ref.parts[2])
        elif ref.last_part == "private_hosted_zone":
            resource = self.get_stack(zone_id=ref.parts[2]).resource
            # legacy support
            if schemas.IRoute53Resource.providedBy(resource):
                return resource.hosted_zones[ref.parts[2]].private_hosted_zone
            return self.get_stack(zone_id=ref.parts[2]).resource.private_hosted_zone

        return None

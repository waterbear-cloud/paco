import paco.cftemplates
from paco.stack_group import StackEnum, StackOrder, Stack, StackGroup
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode


class Route53StackGroup(StackGroup):
    def __init__(self, paco_ctx, account_ctx, route53_config, controller):
        aws_name = account_ctx.get_name()
        super().__init__(paco_ctx,
                         account_ctx,
                         'Route53',
                         aws_name,
                         controller)

        # Initialize config with a deepcopy of the project defaults
        self.config = route53_config
        self.account_ctx = account_ctx
        self.zone_stack_map = {}
        if self.paco_ctx.legacy_flag('route53_hosted_zone_2019_10_12') == True:
            self.init_legacy()
        else:
            self.init_hosted_zones()

    def init_hosted_zones(self):
        for zone_id in self.config.get_zone_ids(account_name=self.account_ctx.get_name()):
            zone_config = self.config.hosted_zones[zone_id]
            route53_template = paco.cftemplates.Route53HostedZone(
                self.paco_ctx,
                self.account_ctx,
                self.paco_ctx.project['credentials'].aws_default_region,
                self, # stack_group
                None, # stack_tags
                zone_config,
                zone_config.paco_ref_parts
            )
            route53_stack = route53_template.stack
            route53_stack.set_termination_protection(True)
            self.zone_stack_map[zone_id] = route53_stack

    def init_legacy(self):
        config_ref = 'resource.route53'
        route53_template = paco.cftemplates.Route53(self.paco_ctx,
                                                self.account_ctx,
                                                self.paco_ctx.project['credentials'].aws_default_region,
                                                self, # stack_group
                                                None, # stack_tags
                                                self.config,
                                                config_ref)

        route53_stack = route53_template.stack
        route53_stack.set_termination_protection(True)
        self.zone_stack_map['legacy'] = route53_stack

    def has_zone_id(self, zone_id):
        if self.config.account_has_zone(self.account_ctx.get_name(), zone_id):
            return True
        return False

    def get_stack(self, zone_id):
        if self.paco_ctx.legacy_flag('route53_hosted_zone_2019_10_12') == True:
            return self.zone_stack_map['legacy']
        elif zone_id in self.zone_stack_map.keys():
            return self.zone_stack_map[zone_id]
        return None

    def validate(self):
        super().validate()

    def provision(self):
        #self.validate()
        super().provision()

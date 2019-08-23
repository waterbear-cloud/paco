import aim.cftemplates
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode


class Route53StackGroup(StackGroup):
    def __init__(self, aim_ctx, account_ctx, route53_config, controller):
        aws_name = account_ctx.get_name()
        super().__init__(aim_ctx,
                         account_ctx,
                         'Route53',
                         aws_name,
                         controller)

        # Initialize config with a deepcopy of the project defaults
        self.config = route53_config
        self.stack_list = []
        config_ref = 'resource.route53'
        route53_template = aim.cftemplates.Route53(self.aim_ctx,
                                                   self.account_ctx,
                                                   self.aim_ctx.project['credentials'].aws_default_region,
                                                   route53_config,
                                                   config_ref)

        route53_stack = Stack(self.aim_ctx,
                              self.account_ctx,
                              self,
                              route53_template,
                              aws_region=self.aim_ctx.project['credentials'].aws_default_region)
        route53_stack.set_termination_protection(True)
        self.stack_list.append(route53_stack)

        self.add_stack_order(route53_stack)


    def has_zone_id(self, zone_id):
        if self.config.account_has_zone(self.account_ctx.get_name(), zone_id):
            return True
        return False

    def get_stack(self, zone_id):
        if self.config.account_has_zone(self.account_ctx.get_name(), zone_id):
            return self.stack_list[0]
        return None

    def validate(self):
        super().validate()

    def provision(self):
        #self.validate()
        super().provision()

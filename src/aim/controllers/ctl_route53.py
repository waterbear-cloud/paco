import os
from aim.stack_group import Route53StackGroup
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.controllers.controllers import Controller

class Route53Controller(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Service",
                         "Route53")
        if not 'route53' in self.aim_ctx.project:
            self.init_done = True
            return
        self.config = self.aim_ctx.project['route53']
        if self.config != None:
            self.config.resolve_ref_obj = self

        #self.aim_ctx.log("Route53 Service: Configuration: %s" % (name))

        self.stack_grps = []
        self.second = False
        self.init_done = False

    def init(self, init_config):
        if self.init_done:
            return
        self.config.resolv_ref_obj = self
        self.init_done = True
        self.init_stack_groups()

    def init_stack_groups(self):
        # TODO: Fixed above now with init done flag?
        if self.second == True:
            raise StackException(AimErrorCode.Unknown)
        self.second = True
        for account_name in self.config.get_hosted_zones_account_names():
            account_ctx = self.aim_ctx.get_account_context(account_name=account_name)
            route53_stack_grp = Route53StackGroup(self.aim_ctx,
                                                  account_ctx,
                                                  self.config,
                                                  self)
            self.stack_grps.append(route53_stack_grp)

    def validate(self):
        for stack_grp in self.stack_grps:
            stack_grp.validate()

    def provision(self):
        for stack_grp in self.stack_grps:
            stack_grp.provision()

    def get_stack(self, zone_id):
        for stack_grp in self.stack_grps:
            if stack_grp.has_zone_id(zone_id):
                return stack_grp.get_stack(zone_id)
        return None

    def resolve_ref(self, ref):
        # route53.example.id
        if ref.last_part == "id":
            return self.get_stack(zone_id=ref.parts[2])

        return None

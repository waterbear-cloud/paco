from paco.stack.stack import BaseStack
from paco.stack.interfaces import IBotoStack
from zope.interface import implementer


@implementer(IBotoStack)
class BotoStack(BaseStack):
    """
    Represents an AWS Resource that is provisioned using Boto3 API calls
    """
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        stack_group,
        resource,
        template=None,
        stack_suffix=None,
        aws_region=None,
        hooks=None,
        do_not_cache=False,
        stack_tags=None,
        change_protected=None,
        support_resource_ref_ext=None,
        extra_context=None,
        enabled=True,
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            stack_group,
            resource,
            template,
            stack_suffix,
            aws_region,
            hooks,
            do_not_cache,
            stack_tags,
            change_protected,
            support_resource_ref_ext,
        )
        self.extra_context = extra_context
        self.enabled = enabled

    def provision(self):
        "Provision Resource"
        raise NotImplemented

    def validate(self):
        "Validate Resource"
        pass

    def delete(self):
        "Delete Resource"
        pass

    def get_outputs(self):
        "Get all Outputs of a Resource"
        raise NotImplemented

    def get_outputs_value(self, key):
        "Get Stack OutputValue by Stack OutputKey"
        if key in self.outputs_value_cache.keys():
            return self.outputs_value_cache[key]
        self.outputs_value_cache = self.get_outputs()
        return self.outputs_value_cache[key]

    def get_status(self):
        "Status of the Stack in AWS"
        raise NotImplemented

    def get_name(self):
        "Name of the Stack in AWS"
        name = '-'.join([ self.grp_ctx.get_aws_name(), self.resource.name ])
        if self.stack_suffix != None:
            name = name + '-' + self.stack_suffix
        new_name = self.create_stack_name(name)
        return new_name

    def wait_for_complete(self):
        "Boto has not concept of wait, but this will be called after provision API calls"
        # handle success actions
        self.stack_success()

        # run post hooks
        if self.action == "create":
            self.hooks.run("create", "post", self)
        elif self.action == "update":
            self.hooks.run("update", "post", self)
        elif self.action == "delete":
            self.hooks.run("delete", "post", self)

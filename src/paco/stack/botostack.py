from paco.stack import Stack

class BotoStack(Stack):
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

    def get_outputs_value(self, key):
        raise NotImplemented

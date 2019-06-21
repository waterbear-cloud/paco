from aim.config.config import Config
import os
import copy
from aim.models import vocabulary


# Config Schema
#
# buckets:
#   <bucket_id>:
#     name: <bucket name>
#     policy:
#       - aws:
#           - aim.sub '${netenv.ref aimdemo.iam.app.roles.instance_role.arn}'
#         effect: 'Allow'
#         action:
#           - 's3:Get*'
#           - 's3:List*'
#         resource_suffix:
#           - '/*'
#           - ''


class S3Config(Config):
    def __init__(self,
                 aim_ctx,
                 region,
                 bucket_name_prefix,
                 bucket_name_suffix,
                 config_ref,
                 config_name,
                 config_dict=None):
        #aim_ctx.log("S3Config Init")

        config_folder = os.path.join(aim_ctx.config_folder, "Services")
        super().__init__(aim_ctx, config_folder, "S3")
        self.config_ref = config_ref
        #self.name = config_name
        self.config_dict = config_dict
        self.bucket_name_prefix = bucket_name_prefix
        self.bucket_name_suffix = ""
        if bucket_name_suffix != None:
            self.bucket_name_suffix = bucket_name_suffix.lower() + "-"
        self.bucket_name_suffix += vocabulary.aws_regions[region]['short_name']
        self.region = region

    def load_defaults(self):
        # TODO: Loading defaults blows away self.config_dict, mitigate this.
        raise StackException(AimErrorCode.Unknown)
        super().load()
        defaults_config = []
        default_config['defaults'] = self.config_dict['defaults']
        self.config_dict = default_config

    def merge_in_config(self, merge_config):
        new_config = self.config_override(self.config_dict, merge_config)
        self.config_dict = new_config

    def enabled(self):
        if "enabled" not in self.config_dict:
            return False
        return self.config_dict['enabled']

    def get_bucket_ids(self, app_id, grp_id):
        return sorted(self.config_dict[app_id][grp_id].keys())

    def get_bucket_name(self, app_id, grp_id, bucket_id):
        bucket_name = self.config_dict[app_id][grp_id][bucket_id].name.lower()
        bucket_name = '-'.join([self.bucket_name_prefix, bucket_name, self.bucket_name_suffix])
        return bucket_name.replace('_', '').lower()

    def get_bucket_arn(self, app_id, grp_id, bucket_id):
        return 'arn:aws:s3:::'+self.get_bucket_name(app_id, grp_id, bucket_id)

    def has_bucket_policy(self, app_id, grp_id, bucket_id):
        policy = self.config_dict[app_id][grp_id][bucket_id].policy
        if policy != None and len(policy) > 0:
            return True
        return False

    def get_bucket_policy_list(self, app_id, grp_id, bucket_id):
        return self.config_dict[app_id][grp_id][bucket_id].policy

    # Deletion Policy
    #   - retain
    #   - delete
    def get_bucket_deletion_policy(self, app_id, grp_id, bucket_id):

        return self.config_dict[app_id][grp_id][bucket_id].deletion_policy

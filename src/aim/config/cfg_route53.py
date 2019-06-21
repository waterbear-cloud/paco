from aim.config.config import Config
import os
import copy


class Route53Config(Config):
    def __init__(self, aim_ctx):
        # config/Services/Route53.yaml
        config_folder = os.path.join(aim_ctx.config_folder, "Services")
        super().__init__(aim_ctx, config_folder, "Route53")
        #self.aim_ctx.log("Route53Config Loaded: %s, Yaml: %s" % (name, self.yaml_path))
        self.load()
        # Default region as Route53 is Global
        self.aws_region = 'us-west-2'
        # Sort zones by Account
        self.zones_by_account = {}
        for zone_id in self.get_zone_ids():
            aws_account = self.get_account(zone_id)
            ref_dict = self.aim_ctx.parse_ref(aws_account)
            account_name = ref_dict['ref_parts'][1]
            if account_name not in self.zones_by_account:
                self.zones_by_account[account_name] = []
            self.zones_by_account[account_name].append(zone_id)

    def load(self):
        super().load()

    def enabled(self, zone_id):
        if 'enabled' not in self.config_dict[zone_id]:
            return None
        return self.config_dict[zone_id]['enabled']

    def get_zone_ids(self, account_name=None):
        if account_name != None:
            return self.zones_by_account[account_name]
        return sorted(self.config_dict.keys())

    def get_account(self, zone_id):
        return self.config_dict[zone_id]['aws_account']

    def get_account_names(self):
        return sorted(self.zones_by_account.keys())

    def get_record_set_ids(self, zone_id):
        if self.has_record_sets(zone_id):
            return sorted(self.config_dict[zone_id]['record_sets'].keys())
        return []

    def get_record_set_domain_name(self, zone_id, record_set_id):
        return self.config_dict[zone_id]['record_sets'][record_set_id]['domain_name']

    def get_hosted_zone_domain_name(self, zone_id):
        return self.config_dict[zone_id]['domain_name']

    def account_has_zone(self, account_name, zone_id):
        if zone_id in self.zones_by_account[account_name]:
            return True
        return False

    def has_record_sets(self, zone_id):
        if 'record_sets' in self.config_dict[zone_id]:
            return True
        return False

    def get_record_set_type(self, zone_id, record_id):
        if not self.has_record_sets(zone_id):
            return None
        return self.config_dict[zone_id]['record_sets'][record_id]['type']

    def get_record_set_ttl(self, zone_id, record_id):
        if not self.has_record_sets(zone_id):
            return None
        if 'ttl' in self.config_dict[zone_id]['record_sets'][record_id]:
            return self.config_dict[zone_id]['record_sets'][record_id]['ttl']
        return None

    def record_set_has_alias_target(self, zone_id, record_id):
        if not self.has_record_sets(zone_id):
            return None
        if 'alias_target' in self.config_dict[zone_id]['record_sets'][record_id]:
            return True
        return False

    def get_record_set_has_alias_target(self, zone_id, record_id):
        if not self.has_record_sets(zone_id):
            return None
        if 'alias_target' in self.config_dict[zone_id]['record_sets'][record_id]:
            return self.config_dict[zone_id]['record_sets'][record_id]['alias_target']
        return None

    def get_record_set_resource_records(self, zone_id, record_id):
        if not self.has_record_sets(zone_id):
            return None
        if 'resource_records' in self.config_dict[zone_id]['record_sets'][record_id]:
            return self.config_dict[zone_id]['record_sets'][record_id]['resource_records']
        return None

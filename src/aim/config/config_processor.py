import json
import boto3
import aim
import os

from botocore.exceptions import ClientError
#import logging
#logging.basicConfig(level=logging.DEBUG)

class ConfigProcessor(object):
    """
    Receives the configuration YAML  as the ModelLoader reads in configuration
    """

    def __init__( self, aim_ctx):
        # The relative path to the Configuration Folder
        self.aim_ctx = aim_ctx
        self.applied_folder = os.path.join(self.aim_ctx.home.rstrip('/')+"_Applied")

    # Receives each YAML file loaded by the ModelLoader
    def load_yaml(self, sub_folder, filename):
        full_yaml_path = os.path.join(self.aim_ctx.project_folder, sub_folder, filename)
        applied_yaml_path = os.path.join(self.aim_applied_fodler)
        print("Full Yaml: %s" % (full_yaml_path))

        pass

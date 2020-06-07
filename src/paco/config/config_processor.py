import json
import boto3
import paco
import os

from botocore.exceptions import ClientError
#import logging
#logging.basicConfig(level=logging.DEBUG)

class ConfigProcessor(object):
    """
    Receives the configuration YAML  as the ModelLoader reads in configuration
    """

    def __init__( self, paco_ctx):
        # The relative path to the Configuration Folder
        self.paco_ctx = paco_ctx
        self.applied_folder = os.path.join(str(self.paco_ctx.home).rstrip('/') + "_Applied")

    # Receives each YAML file loaded by the ModelLoader
    def load_yaml(self, sub_folder, filename):
        full_yaml_path = os.path.join(str(self.paco_ctx.project_folder), sub_folder, filename)
        applied_yaml_path = os.path.join(self.paco_applied_folder)
        print("Full Yaml: %s" % (full_yaml_path))

        pass

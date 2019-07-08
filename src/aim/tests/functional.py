"""
Functional test suite for AIM
"""

import aim.models
import boto3
import os
import pexpect
import requests
import shutil
import sys
import subprocess
from aim.models.references import AimReference
from aim.config.aim_context import AimContext


def init_test_dir():
    subprocess.call(["mkdir","aim_ftest"])
    os.chdir('aim_ftest')
    shutil.rmtree('tproj')

def test_cmd_init():
    print("Testing 'aim init project'")
    child = pexpect.spawn('aim init project')
    child.logfile = sys.stdout.buffer
    child.expect('.*Choose.*')
    child.sendline('2')
    child.expect('project_name .*: ')
    child.sendline('tproj')
    child.expect('project_title .*: ')
    child.sendline('Test Project')
    child.expect('network_environment_name .*: ')
    child.sendline('tnet')
    child.expect('network_environment_title .*: ')
    child.sendline('Test Network')
    child.expect('application_name .*: ')
    child.sendline('tapp')
    child.expect('application_title .*: ')
    child.sendline('Test Application')
    child.expect('aws_default_region .*: ')
    child.sendline('us-west-2')
    child.expect('master_account_id .*: ')
    child.sendline(os.environ['AIM_MASTER_ACCOUNT_ID'])
    child.expect('master_admin_iam_username .*: ')
    child.sendline(os.environ['AIM_MASTER_ADMIN_IAM_USERNAME'])
    child.expect('aws_access_key_id .*: ')
    child.sendline(os.environ['AIM_AWS_ACCESS_KEY_ID'])
    child.expect('aws_secret_access_key .*: ')
    child.sendline(os.environ['AIM_AWS_SECRET_ACCESS_KEY'])
    child.interact()

def test_cmd_provision_keypair():
    print("Testing 'aim provision EC2 keypair'")
    child = pexpect.spawn('aim provision EC2 keypair aimkeypair --home tproj')
    child.logfile = sys.stdout.buffer
    child.interact()

def test_cmd_provision_netenv():
    print("Testing 'aim provsion NetEnv tnet'")
    child = pexpect.spawn('aim provision NetEnv tnet --home tproj')
    child.logfile = sys.stdout.buffer
    child.interact()

def test_web_server_responds():
    project = aim.models.load_project_from_yaml(AimReference(), 'tproj')
    web_asg = project['ne']['tnet']['dev']['us-west-2'].applications['tapp'].groups['site'].resources['alb']
    aim_ctx = AimContext('tproj')
    aim_ctx.init_project()
    account = aim_ctx.get_account_context(account_name='master')
    client = account.get_aws_client('elbv2')
    response = client.describe_load_balancers(Names=[web_asg.resource_name])
    dns_name = response['LoadBalancers'][0]['DNSName']
    response = requests.get('http://' + dns_name)
    assert response.text, '<html><body><h1>Hello world!</h1></body></html>\n'

def main():
    print("Starting AIM functional tests")
    test_web_server_responds()
    sys.exit()
    init_test_dir()
    test_cmd_init()
    test_cmd_provision_keypair()
    test_cmd_provision_netenv()


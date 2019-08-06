"""
Test harnesses for aim init cookiecutter templates
"""

import aim.models
import boto3
import os
import pexpect
import requests
import shutil
import sys
import subprocess


starting_template_mapping = {
    'simple-web-app': '2',
}

def test_cookiecutter_template(starting_template, template_number, verbose):
    init_test_dir()
    test_cmd_init(verbose)
    test_cmd_provision_keypair(verbose)
    test_cmd_provision_netenv(verbose)
    fname = starting_template.replace('-','_')
    function = getattr(aim.commands.cookiecutter_test, 'test_provisioned_{}'.format(fname))
    function(verbose)
    test_delete_netenv(verbose)

def init_test_dir():
    """Create a tmpdir for tests to run in"""
    # ToDo: make a real tmpdir ...
    subprocess.call(["mkdir","aim_ftest"])
    os.chdir('aim_ftest')
    try:
        shutil.rmtree('tproj')
    except FileNotFoundError:
        pass

def test_cmd_init(verbose):
    print("Testing 'aim init project'")
    child = pexpect.spawn('aim init project')
    if verbose:
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

def test_cmd_provision_keypair(verbose):
    print("Testing 'aim provision EC2 keypair'")
    child = pexpect.spawn('aim provision EC2 keypair aimkeypair --home tproj')
    if verbose:
        child.logfile = sys.stdout.buffer
    child.interact()

def test_cmd_provision_netenv(verbose):
    print("Testing 'aim provsion NetEnv tnet'")
    child = pexpect.spawn('aim provision NetEnv tnet --home tproj')
    if verbose:
        child.logfile = sys.stdout.buffer
    child.interact()

def test_delete_netenv(verbose):
    print("Deleting 'aim delete NetEnv tnet --home tproj'")
    child = pexpect.spawn('aim delete NetEnv tnet --home tproj')
    if verbose:
        child.logfile = sys.stdout.buffer
    child.expect('.*Proceed with deletion.*')
    child.sendline('y')
    child.interact()

# Tests for simple-web-app

def test_web_server_responds(verbose):
    project = aim.models.load_project_from_yaml('tproj')
    web_asg = project['ne']['tnet']['dev']['us-west-2'].applications['tapp'].groups['site'].resources['alb']
    aim_ctx = AimContext('tproj')
    aim_ctx.load_project()
    account = aim_ctx.get_account_context(account_name='master')
    client = account.get_aws_client('elbv2')
    response = client.describe_load_balancers(Names=[web_asg.resource_name])
    dns_name = response['LoadBalancers'][0]['DNSName']
    response = requests.get('http://' + dns_name)
    assert response.text, '<html><body><h1>Hello world!</h1></body></html>\n'

def test_provisioned_simple_web_app(verbose):
    test_web_server_responds(verbose)



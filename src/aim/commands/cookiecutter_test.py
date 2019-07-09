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
from aim.config.aim_context import AimContext
from aim.models.references import AimReference

starting_template_mapping = {
    'simple-web-app': '2',
    'complete-web-app': '3',
}

def test_cookiecutter_template(starting_template, template_number, verbose, check_only):
    if not check_only:
        init_test_dir()
        test_cmd_init(verbose)
        test_cmd_provision_keypair(verbose)
        test_cmd_provision_netenv(verbose)
    fname = starting_template.replace('-','_')
    function = getattr(aim.commands.cookiecutter_test, 'test_provisioned_{}'.format(fname))
    function(verbose)
    if not check_only:
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

# Test checks

def check_http(aim_ctx, resource, method='GET', response_code=None, response_text=None, max_retries=5, time_between_retries=5):
    """
    Checks an AIM resource with an HTTP call and validates that it returns the correct response code or text
    """
    check_pass = True
    msg = ''
    # ToDo: look-up IP if bare EC2 ASG
    account = resource.get_account()
    account_context = aim_ctx.get_account_context(account_name=account.name)
    client = account_context.get_aws_client('elbv2')
    response = client.describe_load_balancers(Names=[resource.resource_name])
    dns_name = response['LoadBalancers'][0]['DNSName']
    url = 'http://' + dns_name
    response = requests.get(url)
    if response_code:
        if int(response.status_code) != response_code:
            check_pass = False
            msg += 'URL {} expected response of {} but returned {}\n'.format(
                url, response, response.status_code
            )
    if response_text:
        if response.text.find(response_text) == -1:
            check_pass = False
            msg += 'URL {} expected return text of {} was not found.\n'.format(
                url, response_text
            )
    return check_pass, msg


# Tests for simple-web-app

def test_web_server_responds(verbose):
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

def test_provisioned_simple_web_app(verbose):
    test_web_server_responds(verbose)

# Tests for complete-web-app

def test_provisioned_complete_web_app(verbose):
    aim_ctx = AimContext('aproj')
    aim_ctx.init_project()
    project = aim.models.load_project_from_yaml(AimReference(), 'aproj')
    resource = project['ne']['anet']['dev']['eu-central-1'].applications['myapp'].groups['site'].resources['alb']
    check_pass, msg = check_http(aim_ctx, resource, response_code=200, response_text='<h1>Hello world!</h1>')
    assert check_pass, True



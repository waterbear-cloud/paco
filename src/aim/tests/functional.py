"""
Functional test suite for AIM
"""

import os
import sys
import subprocess
import pexpect

def init_test_dir():
    subprocess.call(["mkdir","aim_ftest"])
    os.chdir('aim_ftest')

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
    child.sendline(os.environ['master_account_id'])
    child.expect('master_admin_iam_username .*: ')
    child.sendline(os.environ['master_admin_iam_username'])
    child.expect('aws_access_key_id .*: ')
    child.sendline(os.environ['aws_access_key_id'])
    child.expect('aws_secret_access_key .*: ')
    child.sendline(os.environ['aws_secret_access_key'])
    child.interact()

def main():
    print("Starting AIM functional tests")
    init_test_dir()
    test_cmd_init()


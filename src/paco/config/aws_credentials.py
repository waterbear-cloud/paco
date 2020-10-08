from paco.core.exception import AuthenticationError
from botocore.exceptions import ClientError
import boto3
import json
import os
import sys


class PacoSTS():
    """
    Provides temporary long term credentials that generate short term credentials by assuming
    a role. When the short term credentials expire, they are regenerated using the long term
    credentials. When the long term credentials expire, the user will be prompted for a new token.
    """
    def __init__(
        self,
        account_ctx=None,
        temp_creds_path=None,
        session_creds_path=None,
        role_creds_path=None,
        mfa_arn=None,
        admin_creds=None,
        admin_iam_role_arn=None,
        org_admin_iam_role_arn=None,
        mfa_account=None,
        mfa_session_expiry_secs=None,
        assume_role_session_expiry_secs=None,
    ):
        # mfa_session_expiry provides long term expiry
        self.mfa_session_expiry_secs = mfa_session_expiry_secs
        # assume_role_session_expiry is restricted to 1 hour due to role chaining.
        self.assume_role_session_expiry_secs = assume_role_session_expiry_secs
        self.temp_creds_path = temp_creds_path
        self.session_creds_path = session_creds_path
        self.role_creds_path = role_creds_path
        self.credentials = None
        self.mfa_arn = mfa_arn
        self.account_ctx = account_ctx
        self.mfa_account = mfa_account
        self.admin_creds = admin_creds
        self.admin_iam_role_arn = admin_iam_role_arn
        self.org_admin_iam_role_arn = org_admin_iam_role_arn
        self.session = None
        self.sts_client = boto3.client('sts')

    def get_temporary_credentials(self):
        return self.credentials

    def load_temp_creds(self, creds_path):
        try:
            with open(creds_path, 'r') as tmp_creds:
                credentials = json.loads(tmp_creds.read())
                client = boto3.client(
                    'sts',
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken']
                )
                _ = client.get_caller_identity()['Account']
        except:
            return None

        return credentials

    def save_temp_creds(self, credentials, creds_path):
        select_creds = {
            'AccessKeyId': credentials['AccessKeyId'],
            'SecretAccessKey': credentials['SecretAccessKey'],
            'SessionToken': credentials['SessionToken'],
        }
        if 'AWSDefaultRegion' in credentials.keys():
            select_creds['AWSDefaultRegion'] = credentials['AWSDefaultRegion']
        with open(creds_path, 'w') as tmp_creds:
            tmp_creds.write(json.dumps(select_creds))
            os.chmod(creds_path, 0o600)

    def create_session_temp_creds(self):
        sts_client = boto3.client('sts',
            region_name=self.admin_creds.aws_default_region,
            aws_access_key_id=self.admin_creds.aws_access_key_id,
            aws_secret_access_key=self.admin_creds.aws_secret_access_key,
        )
        # check that .credentials has properly loaded
        # it's possible to load the model without creds for commands such as `paco init`
        # but once you are asked for MFA you must have a credentials file
        if self.admin_creds.aws_default_region == 'no-region-set':
            print("""
You must have a properly formatted .credentials file to connect to AWS.

Try running `paco init credentials` to create one.
""")
            sys.exit()
        token_code = input('MFA Token: {0}: '.format(self.account_ctx.get_name()))
        session_creds = sts_client.get_session_token(
            DurationSeconds=self.mfa_session_expiry_secs,
            TokenCode=token_code,
            SerialNumber=self.mfa_arn,
        )['Credentials']
        session_creds['AWSDefaultRegion'] = self.admin_creds.aws_default_region
        self.save_temp_creds(session_creds, self.session_creds_path)
        return session_creds

    def get_assume_role_temporary_credentials(self, session_creds):
        "Get AssumeRole temporary credentials"
        role_creds = None
        sts_client = boto3.client(
            'sts',
            region_name=session_creds['AWSDefaultRegion'],
            aws_access_key_id=session_creds['AccessKeyId'],
            aws_secret_access_key=session_creds['SecretAccessKey'],
            aws_session_token=session_creds['SessionToken'],
        )
        for admin_iam_role_arn in [self.admin_iam_role_arn, self.org_admin_iam_role_arn]:
            try:
                role_creds = sts_client.assume_role(
                    DurationSeconds=self.assume_role_session_expiry_secs,
                    RoleArn=admin_iam_role_arn,
                    RoleSessionName='paco-multiaccount-session',
                )['Credentials']
            except ClientError as e:
                if admin_iam_role_arn == self.org_admin_iam_role_arn:
                    message = '{}\n'.format(e)
                    message += 'Unable to assume roles: {}\n'.format(self.admin_iam_role_arn)
                    message += '                        {}\n'.format(self.org_admin_iam_role_arn)
                    raise AuthenticationError(message)
            else:
                self.save_temp_creds(role_creds, self.role_creds_path)
                break
        return role_creds

    def get_temporary_session(self):
        """
        1. Load Temporary AssumeRole Credentials
            1.1 If NOT exist: Load Temporary Session Credentials
                1.1.1 If do NOT exist
                    1.1.1.1 Generate and store Temporary Session Credentials
                    1.1.1.1 Generate and store Temporary Assume Role Creds
        2. If AssumeRole Credentials Expired
            2.1 If Session Credentials expired
                2.1.1 Generate and store Session Credentails
            2.2 Generate and store AssumeRole Credentials from Session
        """
        role_creds = self.load_temp_creds(self.role_creds_path)
        if role_creds == None:
            session_creds = self.load_temp_creds(self.session_creds_path)
            if session_creds == None:
                session_creds = self.create_session_temp_creds()
            role_creds = self.get_assume_role_temporary_credentials(session_creds)

        return boto3.Session(
            aws_access_key_id=role_creds['AccessKeyId'],
            aws_secret_access_key=role_creds['SecretAccessKey'],
            aws_session_token=role_creds['SessionToken'],
        )

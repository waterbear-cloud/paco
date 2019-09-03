import json
import boto3
import aim
import os

from botocore.exceptions import ClientError
#import logging
#logging.basicConfig(level=logging.DEBUG)

class Sts(object):
    """
    Sts: Object to manage the persistence of authentication over multiple
        runs of an automation script. When testing a script this will
        save having to input an MFA token multiple times when using
        an account that requires it.
    """

    def __init__(   self,
                    account_ctx=None,
                    temporary_credentials_path=None,
                    mfa_arn=None,
                    admin_creds=None,
                    admin_iam_role_arn=None,
                    mfa_account=None
                ):
        self.sts_token_expiry_seconds = 3500 # Limited to 1 hour until we use
        self.temp_creds_path = temporary_credentials_path
        self.credentials = None
        self.mfa_arn = mfa_arn
        self.account_ctx = account_ctx
        self.mfa_account = mfa_account
        self.admin_creds = admin_creds
        self.admin_iam_role_arn = admin_iam_role_arn
        self.session = None
        self.sts_client = boto3.client('sts')


    def get_temporary_credentials(self):
        return self.credentials

    def get_temporary_session(self):
        """
        get_temporary_session: checks the temporary credentials stored
            on disk, if they fail to authenticate re-attempt to assume
            the role. The credentials requested last 15 minutes. For
            debugging purposes these can be persisted for up to an hour.
        """
        credentials=None
        try:
            with open(self.temp_creds_path, 'r') as tmp_creds:
                credentials = json.loads(tmp_creds.read())
                client = boto3.client(
                    'sts',
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken']
                )
                _ = client.get_caller_identity()['Account']
        except (IOError, ClientError):
            response = None
            if self.admin_creds != None:
                session = boto3.Session(
                    region_name=self.admin_creds.aws_default_region,
                    aws_access_key_id=self.admin_creds.aws_access_key_id,
                    aws_secret_access_key=self.admin_creds.aws_secret_access_key,
                )

                token_code = input('MFA Token: {0}: '.format(self.account_ctx.get_name()))
                sts_client = session.client('sts')
                response = sts_client.get_session_token(
                    DurationSeconds=(60*60)*6, # 6 hours
                )
                credentials = response['Credentials']
                session = boto3.Session(
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken'],
                    region_name=self.admin_creds.aws_default_region,
                )

                sts_client = session.client('sts')

                response = sts_client.assume_role(
                    DurationSeconds=60*15, # 15 minues
                    RoleArn=self.admin_iam_role_arn,
                    RoleSessionName='aim-multiaccount-session',
                    TokenCode=token_code,
                    SerialNumber=self.mfa_arn
                )
            elif self.mfa_account != None:
                mfa_creds = self.mfa_account.get_temporary_credentials()
                session = boto3.Session(aws_access_key_id=mfa_creds['AccessKeyId'],
                                        aws_secret_access_key=mfa_creds['SecretAccessKey'],
                                        aws_session_token=mfa_creds['SessionToken'])
                response = session.client('sts').assume_role(
                    DurationSeconds=60*15,
                    RoleArn=self.admin_iam_role_arn,
                    RoleSessionName='aim-multiaccount-session')
            # Cache the credentials
            credentials = response['Credentials']
            with open(self.temp_creds_path, 'w') as tmp_creds:
                tmp_creds.write(json.dumps({
                    'AccessKeyId': credentials['AccessKeyId'],
                    'SecretAccessKey': credentials['SecretAccessKey'],
                    'SessionToken': credentials['SessionToken']}))
                os.chmod(self.temp_creds_path, 0o600)
        self.credentials = credentials
        return boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

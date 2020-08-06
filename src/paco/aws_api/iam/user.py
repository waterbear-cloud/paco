
class IAMUserClient():
    """
    IAM User API for managing API Access Keys
    """
    def __init__(self, account_ctx, aws_region, username):
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.username = username

    @property
    def iam_client(self):
        if hasattr(self, '_iam_client') == False:
            self._iam_client = self.account_ctx.get_aws_client('iam', self.aws_region)
        return self._iam_client

    def disable_access_keys(self):
        "Set all User's access keys to Inactive"
        keys_meta = self.iam_client.list_access_keys(UserName=self.username)
        for key_meta in keys_meta['AccessKeyMetadata']:
            if key_meta['Status'] == 'Active':
                print(f"{self.username}: Modifying Access Key Status to: Inactive: {key_meta['AccessKeyId']}")
                self.iam_client.update_access_key(
                    UserName=self.username,
                    AccessKeyId=key_meta['AccessKeyId'],
                    Status='Inactive'
                )

    def enable_access_keys(self):
        keys_meta = self.iam_client.list_access_keys(UserName=self.username)
        for key_meta in keys_meta['AccessKeyMetadata']:
            if key_meta['Status'] == 'Inactive':
                print(f"{self.username}: Modifying Access Key Status to: Active: {key_meta['AccessKeyId']}")
                self.iam_client.update_access_key(
                    UserName=self.username,
                    AccessKeyId=key_meta['AccessKeyId'],
                    Status='Active'
                )

    def list_access_keys(self):
        return self.iam_client.list_access_keys(UserName=self.username)

    def create_access_key(self, key_num):
        "Create an IAM User Access Key"
        access_key_meta = self.iam_client.create_access_key(UserName=self.username)
        access_key_id = access_key_meta['AccessKey']['AccessKeyId']
        secret_key = access_key_meta['AccessKey']['SecretAccessKey']
        print(f"{self.username}: Created Access Key {key_num}: Key Id    : {access_key_id}")
        print(f"{self.username}:                    {key_num}: Secret Key: {secret_key}")
        return access_key_id

    def delete_access_key(self, key_num, access_key_id):
        "Delete an IAM User Access Key"
        self.iam_client.delete_access_key(
            UserName=self.username,
            AccessKeyId=access_key_id,
        )
        print(f"{self.username}: Deleted Access Key {key_num}: Key Id    : {access_key_id}")
        return

    def rotate_access_key(self, key_num, access_key_id):
        "Rotate the IAM User's Access Key"
        print(f"{self.username}: Rotating Access Key {key_num}: Begin")
        self.delete_access_key(key_num, access_key_id)
        new_access_key_id = self.create_access_key(key_num)
        print(f"{self.username}: Rotating Access Key {key_num}: End")
        return new_access_key_id


from paco.config.interfaces import IAccountContext
from paco.models.vocabulary import aws_regions
from botocore.exceptions import ClientError
import io


class PacoBuckets():
    """Paco can create and manage an S3 Bucket for every account/region.
    This can contain configuration used by Paco, such as CloudFormation and
    Lambda code artifacts.

    Paco S3 Buckets are named in the format:

    paco-<project-name>-<account>-<region-short_name>[-<s3bucket-hash>]
    """

    def __init__(self, project):
        self.project = project

    def get_bucket_name(self, account_ctx, region):
        "Name of an Paco S3 Bucket in an account and region"
        short_region = aws_regions[region]['short_name']
        account_name = account_ctx
        if IAccountContext.providedBy(account_ctx):
            account_name = account_ctx.name
        name = f"paco-{self.project.name}-{account_name}-{short_region}"
        if self.project.s3bucket_hash != None:
            name += f"-{self.project.s3bucket_hash}"
        # ToDo: validate bucket name
        return name

    def upload_file(self, file_location, s3_key, account_ctx, region):
        "Upload a file to a Paco Bucket"
        if not self.is_bucket_created(account_ctx, region):
            self.create_bucket(account_ctx, region)
        bucket_name = self.get_bucket_name(account_ctx, region)
        s3_client = account_ctx.get_aws_client('s3', region)
        s3_client.upload_file(file_location, bucket_name, s3_key)
        return bucket_name

    def upload_fileobj(self, file_contents, s3_key, account_ctx, region):
        "Upload a file to a Paco Bucket"
        fileobj = io.BytesIO(file_contents.encode())
        if not self.is_bucket_created(account_ctx, region):
            self.create_bucket(account_ctx, region)
        bucket_name = self.get_bucket_name(account_ctx, region)
        s3_client = account_ctx.get_aws_client('s3', region)
        s3_client.upload_fileobj(fileobj, bucket_name, s3_key)
        return bucket_name

    def get_object(self, s3_key, account_ctx, region):
        """Get an S3 Object from a Paco Bucket and return the body.
        Returns None if the bucket is not created or the object does not exist."""
        if not self.is_bucket_created(account_ctx, region):
            return None
        bucket_name = self.get_bucket_name(account_ctx, region)
        s3_client = account_ctx.get_aws_client('s3', region)
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
            return response["Body"].read()
        except ClientError as error:
            if error.response['Error']['Code'] != 'NoSuchKey':
                raise error
            else:
                return None

    def put_object(self, s3_key, obj, account_ctx, region):
        """Put an S3 Object in a Paco Bucket"""
        if not self.is_bucket_created(account_ctx, region):
            self.create_bucket(account_ctx, region)
        bucket_name = self.get_bucket_name(account_ctx, region)
        s3_client = account_ctx.get_aws_client('s3', region)
        if type(obj) != bytes:
            obj = obj.encode('utf-8')
        s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=obj)
        return bucket_name

    def create_bucket(self, account_ctx, region):
        "Create a Paco S3 Bucket for an account and region"
        bucket_name = self.get_bucket_name(account_ctx, region)
        s3_client = account_ctx.get_aws_client('s3', region)
        # ToDo: check if bucket exists and handle that
        # us-east-1 is a "special default" region - the AWS API behaves differently
        if region == 'us-east-1':
            s3_client.create_bucket(
                ACL='private',
                Bucket=bucket_name,
            )
        else:
            s3_client.create_bucket(
                ACL='private',
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': region,
                },
            )
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status':'Enabled'},
        )
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True,
            }
        )

    def is_bucket_created(self, account_ctx, region):
        "True if the S3 Bucket for the account and region exists"
        bucket_name = self.get_bucket_name(account_ctx, region)
        s3_client = account_ctx.get_aws_client('s3', region)
        try:
            s3_client.get_bucket_location(Bucket=bucket_name)
        except ClientError as error:
            if error.response['Error']['Code'] != 'NoSuchBucket':
                raise error
            else:
                return False
        return True

    def is_object_in_bucket(self, s3_key, account_ctx, region):
        "True if s3_key exists as an object in the S3 Bucket"
        bucket_name = self.get_bucket_name(account_ctx, region)
        s3_client = account_ctx.get_aws_client('s3', region)
        try:
            response = s3_client.head_object(
                Bucket=bucket_name,
                Key=s3_key,
            )
        except ClientError as error:
            if error.response['ResponseMetadata']['HTTPStatusCode'] != 404:
                raise error
            else:
                return False
        return True

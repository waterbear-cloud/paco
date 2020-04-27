from paco.models.vocabulary import aws_regions
from botocore.exceptions import ClientError


class PacoBuckets():
    """Paco can create and manage an S3 Bucket for every account/region.
    This can contain configuration used by Paco, such as CloudFormation and
    Lamda code artifacts.

    Paco S3 Buckets are named in the format:

    paco-<project-name>-<account>-<region-short_name>[-<s3bucket-hash>]
    """

    def __init__(self, project):
        self.project = project

    def get_bucket_name(self, account_ctx, region):
        "Name of an Paco S3 Bucket in an account and region"
        short_region = aws_regions[region]['short_name']
        name = f"paco-{self.project.name}-{account_ctx.name}-{short_region}"
        if self.project.s3bucket_hash != None:
            name += '-self.project.s3bucket_hash'
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

    def create_bucket(self, account_ctx, region):
        "Create a Paco S3 Bucket for an account and region"
        bucket_name = self.get_bucket_name(account_ctx, region)
        s3_client = account_ctx.get_aws_client('s3', region)
        # ToDo: check if bucket exists and handle
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

import boto3
import os
import re
import sys
import traceback
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    """
    Replicate S3 addition/deletion to replica S3 Buckets
    """
    # build S3 bucket name with the ENV Environment Variable
    env_name = os.environ['ENV']
    bucket_basename = 'ne-{{cookiecutter.network_environment_name}}-{}-app-{{cookiecutter.application_name}}-replica-s3-replica-'.format(env_name)

    # parse the aws_regions from the REGION Environment Variable
    regions = os.environ['REGIONS'].split(';')

    # create an S3 boto client
    s3 = boto3.client('s3')
    records = event['Records']
    for record in records:
        src_bucket = record['s3']['bucket']['name']
        src_key = record['s3']['object']['key']
        # replicate additions
        if re.match('^ObjectCreated:*', record['eventName']):
            for region in regions:
                s3.copy_object(
                    ACL='bucket-owner-full-control',
                    Bucket=bucket_basename + region,
                    Key=src_key,
                    CopySource={'Bucket': src_bucket, 'Key': src_key},
                    StorageClass='STANDARD'
                )
        # replicate deletions
        elif re.match('^ObjectRemoved:*', record['eventName']):
            for region in regions:
                s3.delete_object(
                    Bucket=bucket_basename + region,
                    Key=src_key
                )

from paco.core.exception import InvalidFilesystemPath
from paco.utils.zip import patched_make_zipfile
from paco.utils import md5sum
from pathlib import Path
from os.path import basename
import os
import shutil
import tempfile
import zipfile


def create_zip_artifact(artifact_prefix, src_dir):
    "create zip file from directory"
    # patch make_archive so that it includes symbolic links
    # ToDo: excludes __pycache__ - make the excluded files depend upon Lambda runtime
    shutil._ARCHIVE_FORMATS['zip'] = (patched_make_zipfile, [], "ZIP file")
    zip_output = tempfile.gettempdir() + os.sep + artifact_prefix + '.zip'
    if src_dir.is_file():
        zipfile.ZipFile(zip_output, mode='w').write(src_dir, basename(src_dir))
    else:
        shutil.make_archive(zip_output, 'zip', str(src_dir))
    md5_hash = md5sum(zip_output)
    return zip_output, md5_hash

def init_lambda_code(paco_buckets, resource, src, account_ctx, aws_region, is_zip=False):
    "Creates an S3 Bucket and uploads an artifact only if one does not yet exist"
    zip_output = src
    artifact_prefix = f'Paco/LambdaArtifacts/{resource.paco_ref_parts}'
    # create Zip file from src directory
    if not is_zip:
        src_dir = Path(src)
        if not src_dir.exists():
            raise InvalidFilesystemPath(f"Source directory for Lambda code does not exist: {src}")
        zip_output, md5_hash = create_zip_artifact(artifact_prefix, src_dir)
    # create md5 of Zip file
    else:
        md5_hash = md5sum(src)
    artifact_name = f'Paco/LambdaArtifacts/{resource.paco_ref_parts}-{md5_hash}.zip'
    if paco_buckets.is_object_in_bucket(artifact_name, account_ctx, aws_region):
        bucket_name = paco_buckets.get_bucket_name(account_ctx, aws_region)
    else:
        bucket_name, artifact_name = upload_lambda_code(paco_buckets, zip_output, artifact_name, account_ctx, aws_region)
    return bucket_name, artifact_name, md5_hash

def upload_lambda_code(paco_buckets, zip_output, artifact_name, account_ctx, aws_region):
    "Zip up a source directory into an artifact and upload it to a Paco Bucket"
    # src_dir = Path(src)
    # if not src_dir.exists():
    #     raise InvalidFilesystemPath(f"Source directory for Lambda code does not exist: {src}")
    # artifact_name = f'Paco/LambdaArtifacts/{resource.paco_ref_parts}.zip'
    # zip_output, md5_hash = create_zip_artifact(artifact_name, src_dir)

    # upload to Paco Bucket
    bucket_name = paco_buckets.upload_file(zip_output, artifact_name, account_ctx, aws_region)
    return bucket_name, artifact_name

def update_lambda_code(resource, function_name, src, account_ctx, aws_region):
    "Update Lambda function code"
    src_dir = Path(src)
    lambda_client = account_ctx.get_aws_client('lambda', aws_region)
    artifact_name = f'{resource.paco_ref_parts}.zip'
    zip_output, md5_hash = create_zip_artifact(artifact_name, src_dir)
    with open(zip_output,"rb") as f:
        zip_binary = f.read()
    lambda_client.update_function_code(
        FunctionName=function_name,
        ZipFile=zip_binary,
    )

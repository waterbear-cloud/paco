from paco.core.exception import InvalidFilesystemPath
from paco.utils.zip import patched_make_zipfile
from pathlib import Path
import os
import shutil
import tempfile


def create_zip_artifact(artifact_name, src_dir):
    "create zip file from directory"
    # patch make_archive so that it includes symbolic links
    # ToDo: excludes __pycache__ - make the excluded files depend upon Lambda runtime
    shutil._ARCHIVE_FORMATS['zip'] = (patched_make_zipfile, [], "ZIP file")
    zip_output = tempfile.gettempdir() + os.sep + artifact_name
    shutil.make_archive(zip_output, 'zip', str(src_dir))
    return zip_output

def init_lambda_code(paco_buckets, resource, src, account_ctx, aws_region):
    "Creates an S3 Bucket and uploads an artifact only if one does not yet exist"
    artifact_name = f'LambdaArtifacts/{resource.paco_ref_parts}.zip'
    if paco_buckets.is_object_in_bucket(artifact_name, account_ctx, aws_region):
        return paco_buckets.get_bucket_name(account_ctx, aws_region), artifact_name
    else:
        return upload_lambda_code(paco_buckets, resource, src, account_ctx, aws_region)

def upload_lambda_code(paco_buckets, resource, src, account_ctx, aws_region):
    "Zip up a source directory into an artifact and upload it to a Paco Bucket"
    src_dir = Path(src)
    if not src_dir.exists():
        raise InvalidFilesystemPath(f"Source directory for Lambda code does not exist: {src}")
    artifact_name = f'LambdaArtifacts/{resource.paco_ref_parts}.zip'
    zip_output = create_zip_artifact(artifact_name, src_dir)
    # upload to Paco Bucket
    bucket_name = paco_buckets.upload_file(zip_output, artifact_name, account_ctx, aws_region)
    return bucket_name, artifact_name

def update_lambda_code(resource, function_name, src, account_ctx, aws_region):
    "Update Lambda function code"
    src_dir = Path(src)
    lambda_client = account_ctx.get_aws_client('lambda', aws_region)
    artifact_name = f'{resource.paco_ref_parts}.zip'
    zip_output = create_zip_artifact(artifact_name, src_dir)
    with open(zip_output,"rb") as f:
        zip_binary = f.read()
    lambda_client.update_function_code(
        FunctionName=function_name,
        ZipFile=zip_binary,
    )

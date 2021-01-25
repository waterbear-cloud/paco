from paco import cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
from paco.core.exception import InvalidAWSConfiguration
from paco.models.locations import get_parent_by_interface
from paco.models.references import get_model_obj_from_ref
from paco.models.resources import SSMDocument
from paco.models import schemas
from paco.stack import StackHooks
from paco import models
from paco import utils
import json
import os
import pathlib
import shutil


yaml=YAML()
yaml.default_flow_sytle = False

ECR_DEPLOY_SCRIPT_HEAD = """
#!/bin/bash
. {paco_base_path}/EC2Manager/ec2lm_functions.bash

OVERRIDE_SOURCE_DEPLOY_TAG="$1"

declare -a ECR_DEPLOY_LIST=({ecr_deploy_list})

RELEASE_PHASE_TAG='release-phase'
"""

ECR_DEPLOY_SCRIPT_CONFIG = """

{ecr_deploy_name}_SOURCE_REPO_NAME_{idx}='{source_repo_name}'
{ecr_deploy_name}_SOURCE_REPO_DOMAIN_{idx}='{source_repo_domain}'
{ecr_deploy_name}_SOURCE_REPO_URI_{idx}="${{{ecr_deploy_name}_SOURCE_REPO_DOMAIN_{idx}}}/"
{ecr_deploy_name}_SOURCE_TAG_{idx}='{source_tag}'
{ecr_deploy_name}_DEST_REPO_NAME_{idx}='{dest_repo_name}'
{ecr_deploy_name}_DEST_REPO_DOMAIN_{idx}='{dest_repo_domain}'
{ecr_deploy_name}_DEST_REPO_URI_{idx}="${{{ecr_deploy_name}_DEST_REPO_DOMAIN_{idx}}}/"
{ecr_deploy_name}_DEST_TAG_{idx}='{dest_tag}'
{ecr_deploy_name}_RELEASE_PHASE_{idx}=$(echo "{release_phase}" | tr '[:upper:]' '[:lower:]')

"""



ECR_DEPLOY_SCRIPT_BODY = """

function run_command()
{
    DESCRIPTION=$1
    COMMAND=$2
    OUTPUT=$(eval $COMMAND 2>&1)
    EXIT_CODE=$?
    if [ "${DESCRIPTION}" == "" ] ; then
	    DESCRIPTION="${COMMAND}"
    fi
    if [ ${EXIT_CODE} -eq 0 ] ; then
	    echo "${DESCRIPTION}: success"
    else
        echo "ERROR: ${DESCRIPTION}: failed"
        echo "${COMMAND}"
        echo "${OUTPUT}"
        exit ${EXIT_CODE}
    fi
    return 0
}

echo "--------------------------------------------------------------------------"
echo "Pulling from Source"

REPO_LOGIN=[]
for (( I=0; I<${#ECR_DEPLOY_LIST[@]}; I++ ))
do
    ECR_DEPLOY_LEN=${ECR_DEPLOY_LIST[$I]}_ECR_DEPLOY_LEN
    # Login to the ECR Repositories
    echo "Authenticating Docker with the ECR Repositories"
    SOURCE_REPO_AUTH_DONE=""
    DEST_REPO_AUTH_DONE=""
    for (( J=0; J<${!ECR_DEPLOY_LEN}; J++ ))
    do

        SOURCE_REPO_NAME=${ECR_DEPLOY_LIST[$I]}_SOURCE_REPO_NAME_$J
        SOURCE_REPO_DOMAIN=${ECR_DEPLOY_LIST[$I]}_SOURCE_REPO_DOMAIN_$J
        SOURCE_REPO_URI=${ECR_DEPLOY_LIST[$I]}_SOURCE_REPO_URI_$J
        SOURCE_DEPLOY_TAG=${ECR_DEPLOY_LIST[$I]}_SOURCE_TAG_$J
        if [ "${OVERRIDE_SOURCE_DEPLOY_TAG}" != "" ] ; then
            SOURCE_DEPLOY_TAG="OVERRIDE_SOURCE_DEPLOY_TAG"
        fi

        DEST_REPO_NAME=${ECR_DEPLOY_LIST[$I]}_DEST_REPO_NAME_$J
        DEST_REPO_DOMAIN=${ECR_DEPLOY_LIST[$I]}_DEST_REPO_DOMAIN_$J
        DEST_DEPLOY_TAG=${ECR_DEPLOY_LIST[$I]}_DEST_TAG_$J
        DEST_REPO_URI=${ECR_DEPLOY_LIST[$I]}_DEST_REPO_URI_$J

        RELEASE_PHASE=${ECR_DEPLOY_LIST[$I]}_RELEASE_PHASE_$J

        if [[ "${SOURCE_REPO_AUTH_DONE}" != *"${!SOURCE_REPO_DOMAIN}"* ]] ; then
            run_command "docker login source: ${!SOURCE_REPO_DOMAIN}" "aws ecr get-login-password | docker login --username AWS --password-stdin ${!SOURCE_REPO_DOMAIN}"
            SOURCE_REPO_AUTH_DONE="${SOURCE_REPO_AUTH_DONE} ${!SOURCE_REPO_DOMAIN}"
        fi
        if [[ "${DEST_REPO_AUTH_DONE}" != *"${!DEST_REPO_DOMAIN}"* ]] ; then
            run_command "docker login destination: ${!DEST_REPO_DOMAIN}" "aws ecr get-login-password | docker login --username AWS --password-stdin ${!DEST_REPO_DOMAIN}"
            DEST_REPO_AUTH_DONE="${DEST_REPO_AUTH_DONE} ${!DEST_REPO_DOMAIN}"
        fi

        run_command "" "docker pull ${!SOURCE_REPO_URI}${!SOURCE_REPO_NAME[$I]}:${!SOURCE_DEPLOY_TAG}"

        if [ "${!RELEASE_PHASE}" == 'true' ] ; then
            #run_command "docker tag ${!SOURCE_REPO_NAME}:${!SOURCE_DEPLOY_TAG} ${!DEST_REPO_NAME}:${DEPLOY_TAG}" "docker tag ${!SOURCE_REPO_URI}${!SOURCE_REPO_NAME}:${!SOURCE_DEPLOY_TAG} ${!DEST_REPO_URI}${!DEST_REPO_NAME}:${RELEASE_PHASE_TAG}"
            run_command "" "docker tag ${!SOURCE_REPO_URI}${!SOURCE_REPO_NAME}:${!SOURCE_DEPLOY_TAG} ${!DEST_REPO_URI}${!DEST_REPO_NAME}:${RELEASE_PHASE_TAG}"
            run_command "" "docker push ${!DEST_REPO_URI}${!DEST_REPO_NAME}:${RELEASE_PHASE_TAG}"
        fi
    done

    echo "--------------------------------------------------------------------------"
    echo "Release Phase"

    /usr/local/bin/paco-ecs-release-phase-${ECR_DEPLOY_LIST[$I]} ${RELEASE_PHASE_TAG}
    RET=$?
    if [ $RET -ne 0 ] ; then
        echo "ERROR: Release Phase failed. Aborting deployment."
        exit $RET
    fi

    echo "--------------------------------------------------------------------------"
    echo "Ready to deploy source images to destination"
    echo
    read -p "Type 'deploy' to continue: " ANSWER
    if [ "${ANSWER}" != "deploy" ] ; then
        echo "Answer does not match, aborting deployment."
        exit 1
    fi

    echo "--------------------------------------------------------------------------"
    echo "Pushing to Destination"

    for (( J=0; J<${!ECR_DEPLOY_LEN}; J++ ))
    do
        SOURCE_REPO_NAME=${ECR_DEPLOY_LIST[$I]}_SOURCE_REPO_NAME_$J
        SOURCE_REPO_DOMAIN=${ECR_DEPLOY_LIST[$I]}_SOURCE_REPO_DOMAIN_$J
        SOURCE_REPO_URI=${ECR_DEPLOY_LIST[$I]}_SOURCE_REPO_URI_$J
        SOURCE_DEPLOY_TAG=${ECR_DEPLOY_LIST[$I]}_SOURCE_TAG_$J
        if [ "${OVERRIDE_SOURCE_DEPLOY_TAG}" != "" ] ; then
            SOURCE_DEPLOY_TAG="OVERRIDE_SOURCE_DEPLOY_TAG"
        fi

        DEST_REPO_NAME=${ECR_DEPLOY_LIST[$I]}_DEST_REPO_NAME_$J
        DEST_REPO_DOMAIN=${ECR_DEPLOY_LIST[$I]}_DEST_REPO_DOMAIN_$J
        DEST_DEPLOY_TAG=${ECR_DEPLOY_LIST[$I]}_DEST_TAG_$J
        DEST_REPO_URI=${ECR_DEPLOY_LIST[$I]}_DEST_REPO_URI_$J

        #run_command "docker tag ${!SOURCE_REPO_NAME}:${!SOURCE_DEPLOY_TAG} ${!DEST_REPO_NAME}:${!DEST_DEPLOY_TAG}" "docker tag ${!SOURCE_REPO_URI}${!SOURCE_REPO_NAME}:${!SOURCE_DEPLOY_TAG} ${!DEST_REPO_URI}${!DEST_REPO_NAME}:${!DEST_DEPLOY_TAG}"
        run_command "" "docker tag ${!SOURCE_REPO_URI}${!SOURCE_REPO_NAME}:${!SOURCE_DEPLOY_TAG} ${!DEST_REPO_URI}${!DEST_REPO_NAME}:${!DEST_DEPLOY_TAG}"
        #run_command "deploy: docker push ${!DEST_REPO_NAME}:${!DEST_DEPLOY_TAG}" "docker push ${!DEST_REPO_URI}${!DEST_REPO_NAME}:${!DEST_DEPLOY_TAG}"
        run_command "" "docker push ${!DEST_REPO_URI}${!DEST_REPO_NAME}:${!DEST_DEPLOY_TAG}"
    done
done
"""

RELEASE_PHASE_SCRIPT = """#!/bin/bash -e

set -e
# ECS Release Phase Command

IMAGE_TAG="$1"
export AWS_DEFAULT_REGION=$2

# Globals
ECHO_PREFIX="ecs-release-phase"
ECS_INSTANCE_ID=""
TASK_ARN=""
TASK_ID=""
REGISTERED_TASK_DEFINITION=""
REGISTERED_TASK_DEFINITION_ARN=""

# -----------------------------
# Set the global registered task definition variable
function set_registered_task_definition() {
    local TASK_DEFINITION_ARN=$1
    REGISTERED_TASK_DEFINITION_ARN=${TASK_DEFINITION_ARN}
    REGISTERED_TASK_DEFINITION=$(echo $TASK_DEFINITION_ARN | awk -F ':' '{print $6":"$7}' | awk -F '/' '{print $2}')
    echo "${ECHO_PREFIX}: set_registered_task_definition: ${REGISTERED_TASK_DEFINITION}"
}

# -----------------------------
# Register a new task definition
function register_task_definition() {
    local CLUSTER_ID=$1
    local SERVICE_ID=$2
    local RELEASE_PHASE_NAME=$3

    echo "${ECHO_PREFIX}: register_task_definition: ${RELEASE_PHASE_NAME}"

    # Get service task definition
    TASK_DEFINITION=$(aws ecs describe-services --cluster ${CLUSTER_ID} --services ${SERVICE_ID} --query 'services[0].taskDefinition' | tr -d '"')
    TEMP_FILE=$(mktemp)
    # echo "${ECHO_PREFIX}: register_task_definition: aws ecs describe-task-definition --task-definition ${TASK_DEFINITION} >${TEMP_FILE}"
    aws ecs describe-task-definition --task-definition ${TASK_DEFINITION} >${TEMP_FILE}
    SED_PATTERN="s/\\"image\\": \\"(.*):.*\\"/\\"image\\": \\"\\1:${IMAGE_TAG}\\"/g"
    #echo sed -iE "${SED_PATTERN}" ${TEMP_FILE}
    cat ${TEMP_FILE} | sed -E "${SED_PATTERN}" >${TEMP_FILE}.new
    mv ${TEMP_FILE}.new ${TEMP_FILE}

    # remove status, compatibilities, taskDefinitionArn, requiresAttributes, revision
    for FIELD in 'registeredAt' 'registeredBy' 'status' 'compatibilities' 'taskDefinitionArn' 'requiresAttributes' 'revision'
    do
        JQ_PATTERN="del(.taskDefinition.${FIELD})"
        #echo cat "${TEMP_FILE} | jq \\"${JQ_PATTERN}\\" > ${TEMP_FILE}.new"
        cat ${TEMP_FILE} | jq "${JQ_PATTERN}" > ${TEMP_FILE}.new
        mv ${TEMP_FILE}.new ${TEMP_FILE}
    done

    # Remove json that is invalid for 'aws ecs register-task-definition'
    sed -iE 's/^{$//' ${TEMP_FILE}
    sed -iE 's/^.*"taskDefinition": {.*/{/' ${TEMP_FILE}
    sed -iE 's/^}$//' ${TEMP_FILE}

    # Create new task definition
    FAMILY="paco-release-phase-"$(echo ${RELEASE_PHASE_NAME} | tr '.' '-')
    echo "${ECHO_PREFIX}: register_task_definition: registering: ${FAMILY}"
    TASK_DEFINITION_ARN=$(aws ecs register-task-definition --family ${FAMILY} --cli-input-json file://${TEMP_FILE} --query "taskDefinition.taskDefinitionArn" --output text)

    rm ${TEMP_FILE}
    set_registered_task_definition ${TASK_DEFINITION_ARN}
    echo "${ECHO_PREFIX}: register_task_definition: created: ${REGISTERED_TASK_DEFINITION}"
}

# -----------------------------
# Run Task
function run_task() {
    local CLUSTER_ID=$1
    local RELEASE_PHASE_NAME=$2

    echo "${ECHO_PREFIX}: run_task: ${RELEASE_PHASE_NAME}"
    RESPONSE=$(aws ecs run-task --cluster ${CLUSTER_ID} --task-definition ${REGISTERED_TASK_DEFINITION_ARN} --tags "key=PACO-RELEASE-PHASE,value=${RELEASE_PHASE_NAME}" --query 'tasks[0].[taskArn,containerInstanceArn]' --output text)
    TASK_ARN=$(echo $RESPONSE | awk '{print $1}')
    CONTAINER_INSTANCE_ARN=$(echo $RESPONSE | awk '{print $2}')
    TASK_ID=$(echo $TASK_ARN |awk -F '/' '{print $3}')
    ECS_INSTANCE_ID="$(aws ecs describe-container-instances --cluster ${CLUSTER_ID} --container-instances ${CONTAINER_INSTANCE_ARN} --query 'containerInstances[0].ec2InstanceId' --output text)"
    echo "${ECHO_PREFIX}: run-task: pending: ${TASK_ARN}"
    aws ecs wait tasks-running --cluster ${CLUSTER_ID} --task ${TASK_ARN}
    echo "${ECHO_PREFIX}: run-task: running: ${TASK_ARN}"
}


# -----------------------------
# Stop Task
function stop_task() {
    # Task stop
    local CLUSTER_ID=$1
    local TASK_ARN=$2

    echo "${ECHO_PREFIX}: stop_task: stopping: ${TASK_ARN}"
    RESPONSE=$(aws ecs stop-task --cluster ${CLUSTER_ID} --task ${TASK_ARN})
    aws ecs wait tasks-stopped --cluster ${CLUSTER_ID} --task ${TASK_ARN}
    echo "${ECHO_PREFIX}: stop_task: stopped: ${TASK_ARN}"
}

# -----------------------------
# Deregister release TaskDefinition
function deregister_task_definition() {
    echo "${ECHO_PREFIX}: deregister_task_definition: pending: ${REGISTERED_TASK_DEFINITION_ARN}"
    RESPONSE="$(aws ecs deregister-task-definition --task-definition ${REGISTERED_TASK_DEFINITION_ARN})"
    echo "${ECHO_PREFIX}: deregister_task_definition: degregistered: ${REGISTERED_TASK_DEFINITION_ARN}"
}

# -----------------------------
# Checks if a task if a release phase task
# returns "True" | "False"
function is_release_phase_task() {
    local RELEASE_PHASE_NAME=$1
    local TASK_ARN=$2

    TAG_QUERY="tags[?key==\`PACO-RELEASE-PHASE\`][value==\`${RELEASE_PHASE_NAME}\`]"
    aws ecs list-tags-for-resource --resource-arn ${TASK_ARN} --query ${TAG_QUERY} --output text
}

# -----------------------------
# Stale Task Check
function stale_task_check() {
    # Check to make sure the task is not already running, if it is, stop it.
    local CLUSTER_ID=$1
    local RELEASE_PHASE_NAME=$2
    for TASK_ARN in $(aws ecs list-tasks --cluster ${CLUSTER_ID} --query 'taskArns[*]' --output text)
    do
        RELEASE_TASK_RUNNING=$(is_release_phase_task ${RELEASE_PHASE_NAME} ${TASK_ARN})
        if [ "${RELEASE_TASK_RUNNING}" == "True" ] ; then
            echo "${ECHO_PREFIX}: stale_task_check: WARNING: Stopping stale release phase task for ${RELEASE_PHASE_NAME}"
            TASK_DEFINITION_ARN=$(aws ecs describe-tasks --tasks ${TASK_ARN} --cluster ${CLUSTER_ID} --query "tasks[0].taskDefinitionArn" --output text)
            set_registered_task_definition ${TASK_DEFINITION_ARN}
            stop_task ${CLUSTER_ID} ${TASK_ARN}
            deregister_task_definition
        fi
    done
}

# -----------------------------
# Task Docker Exec
function task_docker_exec() {
    local CLUSTER_ID=$1
    local TASK_ID=$2
    local ECS_INSTANCE_ID=$3
    local RELEASE_PHASE_COMMAND="$4"

    RES=0
    echo "${ECHO_PREFIX}: task_docker_exec: command start: ${TASK_ID}"
    echo "${ECHO_PREFIX}: task_docker_exec: command: ${RELEASE_PHASE_COMMAND}"
    echo "${ECHO_PREFIX}: task_docker_exec: Instance Id: ${ECS_INSTANCE_ID}"
    TASK_DOCKER_ID=$(aws ecs describe-tasks --cluster ${CLUSTER_ID} --tasks ${TASK_ID} --query 'tasks[0].containers[0].runtimeId' --output text)
    echo aws ssm send-command --instance-ids ${ECS_INSTANCE_ID} --document-name paco_ecs_docker_exec --parameters TaskId=${TASK_DOCKER_ID},Command="${RELEASE_PHASE_COMMAND}" --query 'Command.CommandId' --output text
    COMMAND_ID=$(aws ssm send-command --instance-ids ${ECS_INSTANCE_ID} --document-name paco_ecs_docker_exec --parameters TaskId=${TASK_DOCKER_ID},Command="${RELEASE_PHASE_COMMAND}" --query 'Command.CommandId' --output text)
    #echo "${ECHO_PREFIX}: task_docker_exec: COMMAND_ID: ${COMMAND_ID}"

    while :
    do
        #echo "aws ssm get-command-invocation --instance-id ${ECS_INSTANCE_ID} --command-id ${COMMAND_ID}"
        COMMAND_STATE="$(aws ssm get-command-invocation --instance-id ${ECS_INSTANCE_ID} --command-id ${COMMAND_ID})"
        #echo "${ECHO_PREFIX}: task_docker_exec: COMMAND_STATE: ${COMMAND_STATE}"

        COMMAND_STATUS="$(echo $COMMAND_STATE | jq -r '.Status')"
        #echo "${ECHO_PREFIX}: task_docker_exec: COMMAND_STATUS: |${COMMAND_STATUS}|"

        if [ "${COMMAND_STATUS}" == "InProgress" ] ; then
            echo "${ECHO_PREFIX}: task_docker_exec: status: ${COMMAND_STATUS}: Waiting for exec to finish"
            sleep 5
            continue
        fi

        COMMAND_STATUS_DETAILS="$(echo $COMMAND_STATE | jq -r '.StatusDetails')"
        echo "${ECHO_PREFIX}: task_docker_exec: COMMAND_STATUS_DETAILS: ${COMMAND_STATUS_DETAILS}"
        COMMAND_STDOUT="$(echo $COMMAND_STATE | jq -r '.StandardOutputContent')"
        echo "${ECHO_PREFIX}: task_docker_exec: COMMAND_STDOUT: ${COMMAND_STDOUT}"

        if [ "${COMMAND_STATUS}" == "Failed" ] ; then
            COMMAND_STDERR="$(echo $COMMAND_STATE | jq -r '.StandardErrorContent')"
            echo "${ECHO_PREFIX}: task_docker_exec: StandardErrorContent: ${COMMAND_STDERR}"
            STATUS_MSG="${COMMAND_STDERR}"
            RES=255
        else
            STATUS_MSG="${COMMAND_STDOUT}"
        fi
        break
    done

    echo "${ECHO_PREFIX}: task_docker_exec: command finished: ${TASK_ID}: ${COMMAND_STATUS}: ${STATUS_MSG}"
    return $RES
}

# -----------------------------
# Task Docker Exec
function run_release_phase() {
    local CLUSTER_ID="$1"
    local SERVICE_ID="$2"
    local RELEASE_PHASE_NAME="$3"
    local RELEASE_PHASE_COMMAND="$4"

    echo "${ECHO_PREFIX}: ECS Relase Phase: ${RELEASE_PHASE_NAME}"

    echo "${ECHO_PREFIX}: CLUSTER_ID: ${CLUSTER_ID}"
    echo "${ECHO_PREFIX}: SERVICE_ID: ${SERVICE_ID}"
    echo "${ECHO_PREFIX}: RELEASE_PHASE_NAME: ${RELEASE_PHASE_NAME}"
    echo "${ECHO_PREFIX}: RELEASE_PHASE_COMMAND: ${RELEASE_PHASE_COMMAND}"

    # 1. Stop any stale tasks if there are any
    stale_task_check ${CLUSTER_ID} ${RELEASE_PHASE_NAME}

    # 2. Register a new task definition for the release phase
    register_task_definition ${CLUSTER_ID} ${SERVICE_ID} ${RELEASE_PHASE_NAME}

    # 3. Run a new task: run-task returns values for global variables: TASK_ARN, TASK_ID, & ECS_INSTANCE_ID
    run_task ${CLUSTER_ID} ${RELEASE_PHASE_NAME}

    # 4. Execute the release phase script
    task_docker_exec ${CLUSTER_ID} ${TASK_ID} ${ECS_INSTANCE_ID} "${RELEASE_PHASE_COMMAND}"
    EXEC_RES=$?

    # 5. stop the task
    stop_task ${CLUSTER_ID} ${TASK_ARN}

    # 6. Deregister the task definition created for the release phase
    deregister_task_definition

    if [ $EXEC_RES -ne 0 ] ; then
        exit $EXEC_RES
    fi

    return $EXEC_RES
}

# ----------------------------------------------------------
# Main

"""

RELEASE_PHASE_SCRIPT_SSM_DOCUMENT_CONTENT = {
                "schemaVersion": "2.2",
                "description": "Paco ECS Release Phase Docker Exec",
                "parameters": {
                    "TaskId": {
                        "type": "String",
                        "description": "ECS Docker Task Id"
                    },
                    "Command": {
                        "type": "String",
                        "description": "Command to execute in the task container"
                    }
                },
                "mainSteps": [
                    {
                        "action": "aws:runShellScript",
                        "name": "ECSTaskDockerExec",
                        "inputs": {
                            "runCommand": [
                                '/usr/bin/docker exec {{TaskId}} {{Command}}',
                            ]
                        }
                    }
                ]
            }

class DeploymentPipelineResourceEngine(ResourceEngine):

    def __init__(self, app_engine, grp_id, res_id, resource, stack_tags):
        super().__init__(app_engine, grp_id, res_id, resource, stack_tags)
        self.pipeline_account_ctx = None
        self.pipeline = resource
        self.kms_stack = None
        self.kms_crypto_principle_list = []
        self.artifacts_bucket_policy_resource_arns = []
        self.artifacts_bucket_meta = {
            'obj': None,
            'ref': None,
            'arn': None,
            'name': None,
        }
        self.codecommit_role_name = 'codecommit_role'
        self.github_role_name = 'github_role'
        self.source_stage = None
        self.codebuild_ecs_release_phase_cache_id = ""

    def init_stage(self, stage_config):
        "Initialize an Action in a Stage: for source/build/deploy-style"
        if stage_config == None:
            return
        for action_name in stage_config.keys():
            action_config = stage_config[action_name]
            action_config.resolve_ref_obj = self
            method_name = 'init_stage_action_' + action_config.type.replace('.', '_').lower()
            method = getattr(self, method_name)
            method(action_config)

    def init_stage_action(self, stage, action):
        "Initialize an Action in a Stage: for flexible stage/action-style"
        # dynamically calls a method with the format:
        # init_action_<action_type>(action)
        action.resolve_ref_obj = self
        method_name = 'init_action_' + action.type.replace('.', '_').lower()
        method = getattr(self, method_name, None)
        if method != None:
            method(stage, action)

    def init_resource(self):
        self.pipeline.resolve_ref_obj = self
        self.pipeline.configuration.resolve_ref_obj = self
        self.pipeline_account_ctx = self.paco_ctx.get_account_context(self.pipeline.configuration.account)

        # S3 Artifacts Bucket:
        s3_ctl = self.paco_ctx.get_controller('S3')
        s3_bucket = get_model_obj_from_ref(self.pipeline.configuration.artifacts_bucket, self.paco_ctx.project)
        self.artifacts_bucket_meta['obj'] = s3_bucket
        self.artifacts_bucket_meta['ref'] = self.pipeline.configuration.artifacts_bucket
        self.artifacts_bucket_meta['arn'] = s3_ctl.get_bucket_arn(self.artifacts_bucket_meta['ref'])
        self.artifacts_bucket_meta['name'] = s3_bucket.get_bucket_name()

        # Resource can be in a Service or an Environment
        if hasattr(self, 'env_ctx'):
            self.base_aws_name = self.env_ctx.get_aws_name()
            self.deploy_region = self.env_ctx.region
        else:
            # deploy region is the same as the Service region
            # ToDo: use-cases to have this be another region?
            self.deploy_region = self.aws_region
            self.base_aws_name = self.stack_group.get_aws_name()

        # KMS Key
        kms_refs = {}
        # Application Account
        kms_refs['paco.ref accounts.{}'.format(self.account_ctx.name)] = None

        # CodeCommit Account(s)
        # ToDo: allows ALL CodeCommit accounts access, filter out non-CI/CD CodeCommit repos?
        for codecommit_group in self.paco_ctx.project['resource']['codecommit'].values():
            for repo in codecommit_group.values():
                kms_refs[repo.account] = None

        for key in kms_refs.keys():
            self.kms_crypto_principle_list.append(
                "paco.sub 'arn:aws:iam::${%s}:root'" % (key)
            )

        # KMS stack
        kms_config_dict = {
            'admin_principal': {
                'aws': [ "!Sub 'arn:aws:iam::${{AWS::AccountId}}:root'" ]
            },
            'crypto_principal': {
                'aws': self.kms_crypto_principle_list
            }
        }
        self.kms_stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.KMS,
            account_ctx=self.pipeline_account_ctx,
            stack_tags=self.stack_tags,
            support_resource_ref_ext='kms',
            extra_context={'kms_config_dict': kms_config_dict}
        )

        # Initialize Stages
        if self.pipeline.stages != None:
            # flexible stages
            self.s3deploy_bucket_refs = {}
            self.s3deploy_delegate_role_arns = {}
            # Initialize actions
            for stage in self.pipeline.stages.values():
                for action in stage.values():
                    self.init_stage_action(stage, action)
            # if there are S3.Deploy actions, provide a Role
            if len(self.s3deploy_bucket_refs.keys()) > 0:
                self.init_s3_deploy_roles()
        else:
            # source/build/deploy-only stages
            self.init_stage(self.pipeline.source)
            self.init_stage(self.pipeline.build)
            self.init_stage(self.pipeline.deploy)

        # CodePipeline
        self.pipeline._stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.CodePipeline,
            account_ctx=self.pipeline_account_ctx,
            stack_tags=self.stack_tags,
            extra_context={
                'base_aws_name': self.base_aws_name,
                'deploy_region': self.deploy_region,
                'app_name': self.app.name,
                'artifacts_bucket_name': self.artifacts_bucket_meta['name']
            },
        )

        # Add Hooks to the CodePipeline Stack
        if self.pipeline.source != None:
            for action in self.pipeline.source.values():
                if action.type == 'ECR.Source':
                    self.add_ecr_source_hooks(action)

        # Add CodeBuild Role ARN to KMS Key principal now that the role is created
        kms_config_dict['crypto_principal']['aws'] = self.kms_crypto_principle_list
        kms_stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.KMS,
            account_ctx=self.pipeline_account_ctx,
            stack_tags=self.stack_tags,
            support_resource_ref_ext='kms',
            extra_context={'kms_config_dict': kms_config_dict}
        )
        kms_stack.set_dependency(self.kms_stack, 'post-pipeline')

        # Get the ASG Instance Role ARN
        if not self.pipeline.is_enabled():
            return

        self.artifacts_bucket_policy_resource_arns.append(
            "paco.sub '${%s}'" % (self.pipeline.paco_ref + '.codepipeline_role.arn')
        )
        cpbd_s3_bucket_policy = {
            'aws': self.artifacts_bucket_policy_resource_arns,
            'action': [ 's3:*' ],
            'effect': 'Allow',
            'resource_suffix': [ '/*', '' ]
        }
        # the S3 Bucket Policy can be added to by multiple DeploymentPipelines
        s3_ctl.add_bucket_policy(self.artifacts_bucket_meta['ref'], cpbd_s3_bucket_policy)

    def init_stage_action_github_source(self, action_config):
        "Initialize a GitHub.Source action"
        if not action_config.is_enabled():
            return

    def init_stage_action_codecommit_source(self, action_config):
        "Initialize an IAM Role for the CodeCommit action"
        if not action_config.is_enabled():
            return

        role_yaml = """
assume_role_policy:
  effect: Allow
  aws:
    - '{0[tools_account_id]:s}'
instance_profile: false
path: /
role_name: CodeCommit
policies:
  - name: DeploymentPipeline
    statement:
      - effect: Allow
        action:
          - codecommit:BatchGetRepositories
          - codecommit:Get*
          - codecommit:GitPull
          - codecommit:List*
          - codecommit:CancelUploadArchive
          - codecommit:UploadArchive
        resource:
          - {0[codecommit_ref]:s}
      - effect: Allow
        action:
          - 's3:*'
        resource:
          - {0[artifact_bucket_arn]:s}
          - {0[artifact_bucket_arn]:s}/*
      - effect: Allow
        action:
          - 'kms:*'
        resource:
          - "!Ref CMKArn"
"""
        codecommit_ref = action_config.codecommit_repository
        role_table = {
            'codecommit_account_id': "paco.sub '${{{0}.account_id}}'".format(codecommit_ref),
            'tools_account_id': self.pipeline_account_ctx.get_id(),
            'codecommit_ref': "paco.sub '${{{0}.arn}}'".format(codecommit_ref),
            'artifact_bucket_arn': self.artifacts_bucket_meta['arn']
        }
        role_config_dict = yaml.load(role_yaml.format(role_table))
        codecommit_iam_role_config = models.iam.Role(self.codecommit_role_name, action_config)
        codecommit_iam_role_config.apply_config(role_config_dict)
        codecommit_iam_role_config.enabled = action_config.is_enabled()

        iam_ctl = self.paco_ctx.get_controller('IAM')
        # The ID to give this role is: group.resource.instance_iam_role
        codecommit_iam_role_id = self.gen_iam_role_id(self.res_id, self.codecommit_role_name)
        self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s.%s.arn}'" % (action_config.paco_ref, self.codecommit_role_name))
        # IAM Roles Parameters
        iam_role_params = [{
            'key': 'CMKArn',
            'value': self.pipeline.paco_ref + '.kms.arn',
            'type': 'String',
            'description': 'DeploymentPipeline KMS Key Arn'
        }]
        codecommit_account_ref = self.paco_ctx.get_ref(action_config.codecommit_repository + '.account')
        codecommit_account_ctx = self.paco_ctx.get_account_context(codecommit_account_ref)
        iam_ctl.add_role(
            account_ctx=codecommit_account_ctx,
            region=self.aws_region,
            resource=self.resource,
            role=codecommit_iam_role_config,
            iam_role_id=codecommit_iam_role_id,
            stack_group=self.stack_group,
            stack_tags=self.stack_tags,
            template_params=iam_role_params,
        )

    def init_action_s3_deploy(self, stage, action):
        "Initialize an IAM Role stack to allow access to the S3 Bucket for the action"
        bucket = get_model_obj_from_ref(action.bucket, self.paco_ctx.project)
        if bucket.account not in self.s3deploy_bucket_refs:
            self.s3deploy_bucket_refs[bucket.account] = {}
        self.s3deploy_bucket_refs[bucket.account][action.bucket] = None

    def init_s3_deploy_roles(self):
        "Create Role for every account with an S3.Deploy bucket to allow access to all S3 Bucket(s) for S3.Deploy Actions in that account"
        for account_ref in self.s3deploy_bucket_refs.keys():
            account = get_model_obj_from_ref(account_ref, self.paco_ctx.project)
            bucket_arns = []
            for ref in self.s3deploy_bucket_refs[account_ref].keys():
                bucket_arn = self.paco_ctx.get_ref(ref + '.arn')
                bucket_arns.append(bucket_arn)
                bucket_arns.append(bucket_arn + '/*')
            role_dict = {
                'assume_role_policy': {'effect': 'Allow', 'aws': [ self.pipeline_account_ctx.get_id() ]},
                'instance_profile': False,
                'path': '/',
                'role_name': 'S3Deploy',
                'enabled': True,
                'policies': [{
                    'name': 'DeploymentPipeline',
                    'statement': [
                        {'effect': 'Allow', 'action': ['s3:*'], 'resource': bucket_arns, },
                        { 'effect': 'Allow',
                          'action': ['s3:*'],
                          'resource': [self.artifacts_bucket_meta['arn'], self.artifacts_bucket_meta['arn'] + '/*']
                        },
                        { 'effect': 'Allow', 'action': 'kms:*', 'resource': ["!Ref CMKArn"] },
                    ]
                }],
            }
            role_name = 's3deploydelegate_{}'.format(account.name)
            role = models.iam.Role(role_name, self.pipeline)
            role.apply_config(role_dict)

            iam_ctl = self.paco_ctx.get_controller('IAM')
            role_id = self.gen_iam_role_id(self.res_id, role_name)
            self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s}'" % (role.paco_ref + '.arn'))

            # IAM Roles Parameters
            iam_role_params = [{
                'key': 'CMKArn',
                'value': self.pipeline.paco_ref + '.kms.arn',
                'type': 'String',
                'description': 'DeploymentPipeline KMS Key Arn'
            }]
            iam_ctl.add_role(
                account_ctx=self.paco_ctx.get_account_context(account_ref),
                region=self.aws_region,
                resource=self.resource,
                role=role,
                iam_role_id=role_id,
                stack_group=self.stack_group,
                stack_tags=self.stack_tags,
                template_params=iam_role_params,
            )
            self.s3deploy_delegate_role_arns[account_ref] = iam_ctl.role_arn(role.paco_ref_parts)

    def init_stage_action_s3_deploy(self, action_config):
        "Initialize an IAM Role stack to allow access to the S3 Bucket for the action"
        # Create a role to allow access to the S3 Bucket
        role_yaml = """
assume_role_policy:
  effect: Allow
  aws:
    - '{0[codepipeline_account_id]}'
instance_profile: false
path: /
role_name: S3
policies:
  - name: DeploymentPipeline
    statement:
      - effect: Allow
        action:
          - s3:*
        resource:
          - {0[bucket_arn]}
          - {0[bucket_arn]}/*
      - effect: Allow
        action:
          - 's3:*'
        resource:
          - {0[artifact_bucket_arn]:s}
          - {0[artifact_bucket_arn]:s}/*
      - effect: Allow
        action:
          - 'kms:*'
        resource:
          - "!Ref CMKArn"
"""
        bucket_config = self.paco_ctx.get_ref(action_config.bucket)
        role_table = {
            'codepipeline_account_id': self.pipeline_account_ctx.get_id(),
            'bucket_account_id': self.account_ctx.get_id(),
            'bucket_arn': self.paco_ctx.get_ref(bucket_config.paco_ref +'.arn'),
            'artifact_bucket_arn': self.artifacts_bucket_meta['arn']
        }

        role_config_dict = yaml.load(role_yaml.format(role_table))
        role_config = models.iam.Role('delegate', action_config)
        role_config.apply_config(role_config_dict)
        role_config.enabled = action_config.is_enabled()

        iam_ctl = self.paco_ctx.get_controller('IAM')
        # The ID to give this role is: group.resource.instance_iam_role
        role_id = self.gen_iam_role_id(self.res_id, 'delegate')
        self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s}'" % (action_config.paco_ref + '.delegate.arn'))
        # IAM Roles Parameters
        iam_role_params = [{
            'key': 'CMKArn',
            'value': self.pipeline.paco_ref + '.kms.arn',
            'type': 'String',
            'description': 'DeploymentPipeline KMS Key Arn'
        }]
        bucket_account_ctx = self.paco_ctx.get_account_context(bucket_config.account)
        role_ref = '{}.delegate'.format(action_config.paco_ref_parts)
        iam_ctl.add_role(
            account_ctx=bucket_account_ctx,
            region=self.aws_region,
            resource=self.resource,
            role=role_config,
            iam_role_id=role_id,
            stack_group=self.stack_group,
            stack_tags=self.stack_tags,
            template_params=iam_role_params,
        )
        action_config._delegate_role_arn = iam_ctl.role_arn(role_ref)


    def init_stage_action_codedeploy_deploy(self, action_config):
        "Initialize a CodeDeploy stack for the action"
        if not action_config.is_enabled():
            return

        self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s}'" % (action_config.paco_ref + '.codedeploy_tools_delegate_role.arn'))
        self.artifacts_bucket_policy_resource_arns.append(self.paco_ctx.get_ref(action_config.auto_scaling_group+'.instance_iam_role.arn'))
        action_config._stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.CodeDeploy,
            stack_tags=self.stack_tags,
            extra_context={
                'base_aws_name': self.base_aws_name,
                'app_name': self.app.name,
                'action_config': action_config,
                'artifacts_bucket_name': self.artifacts_bucket_meta['name'],
            },
        )

    def create_image_definitions_artifact_cache(self, hook, pipeline):
        "Create a cache id for the imageDefinitions service name"
        service = ''
        for action in pipeline.deploy.values():
            if action.type == 'ECS.Deploy':
                service = get_model_obj_from_ref(action.service, self.paco_ctx.project)
            return service.name + ':' + self.artifacts_bucket_meta['obj'].account

    def create_image_definitions_artifact(self, hook, pipeline):
        "Create an imageDefinitions file"
        ecr_uri = None
        service = None
        for action in pipeline.source.values():
            if action.type == 'ECR.Source':
                ecr_uri = f"{self.pipeline_account_ctx.get_id()}.dkr.ecr.{self.aws_region}.amazonaws.com/{action.repository}:{action.image_tag}"
        for action in pipeline.deploy.values():
            if action.type == 'ECS.Deploy':
                service = get_model_obj_from_ref(action.service, self.paco_ctx.project)
        file_contents = f"""[
  {{
    "name": "{service.name}",
    "imageUri": "{ecr_uri}"
  }}
]
"""
        # Create temp zip file of the imageDefinitions.json
        orig_cwd = os.getcwd()
        work_path = pathlib.Path(self.paco_ctx.build_path)
        work_path = work_path / 'DeploymentPipeline' / self.app.paco_ref_parts / self.pipeline_account_ctx.get_name()
        work_path = work_path / self.aws_region / self.app.name / self.resource.group_name / self.resource.name / 'ImageDefinitions'
        zip_path = work_path / 'zip'
        pathlib.Path(zip_path).mkdir(parents=True, exist_ok=True)
        os.chdir(zip_path)
        utils.write_to_file(zip_path, 'imagedefinitions.json', file_contents)
        archive_path = work_path / 'imagedef'
        shutil.make_archive(archive_path, 'zip', zip_path)
        os.chdir(orig_cwd)

        # Upload to S3
        bucket_name = self.artifacts_bucket_meta['name']
        s3_key = self.pipeline._stack.get_name() + '-imagedef.zip'
        bucket_account_ctx = self.paco_ctx.get_account_context(self.artifacts_bucket_meta['obj'].account)
        bucket_s3_client = bucket_account_ctx.get_aws_client('s3')
        pipeline_s3_client = self.pipeline_account_ctx.get_aws_client('s3')
        canonical_id = pipeline_s3_client.list_buckets()['Owner']['ID']
        bucket_s3_client.upload_file(
            str(archive_path) + '.zip',
            bucket_name,
            s3_key,
            ExtraArgs={
                'GrantFullControl': 'id="' + canonical_id + '"',
            },
        )

    def init_stage_action_ecr_source(self, action_config):
        "Initialize an ECR Source action"
        if not action_config.is_enabled():
            return

        # KMS principle
        self.kms_crypto_principle_list.append("paco.sub '${%s}'" % (self.pipeline.paco_ref + '.codepipeline_role.arn'))
        s3_bucket = self.artifacts_bucket_meta['obj']
        if s3_bucket.versioning != True:
            raise InvalidAWSConfiguration(f"""The DeploymentPipeline artifact bucket needs versioning enabled to support the ECR.Source action.
Enabled on the S3Bucket resource with `versioning: true`.

DeploymentPipeline: {self.pipeline.paco_ref}
ArtifactsBucket: {s3_bucket.paco_ref}
""")

    def add_ecr_source_hooks(self, action):
        if not action.is_enabled():
            return
        # Hook to create and upload imageDefinitions.json S3 source artifact
        self.pipeline._stack.hooks.add(
            name='CreateImageDefinitionsArtifact.' + self.resource.name,
            stack_action='update',
            stack_timing='post',
            hook_method=self.create_image_definitions_artifact,
            cache_method=self.create_image_definitions_artifact_cache,
            hook_arg=self.pipeline,
        )
        self.pipeline._stack.hooks.add(
            name='CreateImageDefinitionsArtifact.' + self.resource.name,
            stack_action='create',
            stack_timing='post',
            hook_method=self.create_image_definitions_artifact,
            cache_method=self.create_image_definitions_artifact_cache,
            hook_arg=self.pipeline,
        )

    def init_stage_action_ecs_deploy(self, action_config):
        "Initialize an ECS stack for the action"
        if not action_config.is_enabled():
            return

        role_yaml = """
assume_role_policy:
  effect: Allow
  aws:
    - '{0[pipeline_account_id]}'
instance_profile: false
path: /
role_name: ECS
policies:
  - name: DeploymentPipeline
    statement:
      - effect: Allow
        action:
          - 's3:*'
        resource:
          - {0[artifact_bucket_arn]:s}
          - {0[artifact_bucket_arn]:s}/*
      - effect: Allow
        action:
          - 'kms:*'
        resource:
          - "!Ref CMKArn"
      - effect: Allow
        action:
          - 'iam:PassRole'
          - 'ecs:*'
        resource:
          - "*"
"""
        role_table = {
            'pipeline_account_id': self.pipeline_account_ctx.get_id(),
            'artifact_bucket_arn': self.artifacts_bucket_meta['arn']
        }
        role_config_dict = yaml.load(role_yaml.format(role_table))
        role_config = models.iam.Role('ecs-delegate', action_config)
        role_config.apply_config(role_config_dict)
        role_config.enabled = action_config.is_enabled()
        iam_ctl = self.paco_ctx.get_controller('IAM')
        role_id = self.gen_iam_role_id(self.res_id, 'ecs-delegate')
         # IAM Roles Parameters
        iam_role_params = [{
            'key': 'CMKArn',
            'value': self.pipeline.paco_ref + '.kms.arn',
            'type': 'String',
            'description': 'DeploymentPipeline KMS Key Arn'
        }]
        iam_ctl.add_role(
            account_ctx=self.account_ctx,
            region=self.aws_region,
            resource=self.resource,
            role=role_config,
            iam_role_id=role_id,
            stack_group=self.stack_group,
            stack_tags=self.stack_tags,
            template_params=iam_role_params
        )

        self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s}'" % (role_config.paco_ref + '.arn'))
        action_config._delegate_role_arn = iam_ctl.role_arn(role_config.paco_ref_parts)

    def stack_hook_codebuild_ecs_release_phase_cache_id(self, hook, config):
        "Cache method to return a bundle's cache id"
        return self.codebuild_ecs_release_phase_cache_id

    def stack_hook_codebuild_ecs_release_phase(self, hook, config):
        "Uploads the release phase script to an S3 bucket"
        if len(config.release_phase.ecs) == 0:
            return
        # Genreate script
        release_phase_script_name = "release-phase.sh"
        release_phase_script = RELEASE_PHASE_SCRIPT
        idx = 0
        for command in config.release_phase.ecs:
            release_phase_name = command.service.split(' ')[1]
            release_phase_script += f"""
CLUSTER_ID_{idx}=${{PACO_CB_RP_ECS_CLUSTER_ID_{idx}}}
SERVICE_ID_{idx}=${{PACO_CB_RP_ECS_SERVICE_ID_{idx}}}
RELEASE_PHASE_NAME_{idx}={release_phase_name}
RELEASE_PHASE_COMMAND_{idx}="{command.command}"
run_release_phase "${{CLUSTER_ID_{idx}}}" "${{SERVICE_ID_{idx}}}" "${{RELEASE_PHASE_NAME_{idx}}}" "${{RELEASE_PHASE_COMMAND_{idx}}}"
"""
            idx += 1

        unqiue_folder_name = config.paco_ref_parts
        build_folder = os.path.join(self.paco_ctx.build_path, 'ReleasePhase', unqiue_folder_name)
        file_path = os.path.join(build_folder, release_phase_script_name)
        utils.write_to_file(build_folder, release_phase_script_name, release_phase_script)
        self.codebuild_ecs_release_phase_cache_id = utils.md5sum(str_data=release_phase_script)

        s3_ctl = self.paco_ctx.get_controller('S3')
        pipeline_config = get_parent_by_interface(config, schemas.IDeploymentPipeline)
        bucket_name = s3_ctl.get_bucket_name(pipeline_config.configuration.artifacts_bucket)
        s3_client = self.account_ctx.get_aws_client('s3')
        s3_key = os.path.join('ReleasePhase', 'ECS', unqiue_folder_name, release_phase_script_name)
        s3_client.upload_file(file_path, bucket_name, s3_key, ExtraArgs={'ACL':'bucket-owner-full-control'})
        print(f"Release Phase: aws s3 cp s3://{bucket_name}/{s3_key} ./{release_phase_script_name}")

    def codebuild_ecs_release_phase_ssm(self):
        ssm_documents = self.paco_ctx.project['resource']['ssm'].ssm_documents
        if 'paco_ecs_docker_exec' not in ssm_documents:
            ssm_doc = SSMDocument('paco_ecs_docker_exec', ssm_documents)
            ssm_doc.add_location(self.account_ctx.paco_ref, self.aws_region)
            ssm_doc.content = json.dumps(RELEASE_PHASE_SCRIPT_SSM_DOCUMENT_CONTENT)
            ssm_doc.document_type = 'Command'
            ssm_doc.enabled = True
            ssm_documents['paco_ecs_docker_exec'] = ssm_doc
        else:
            ssm_documents['paco_ecs_docker_exec'].add_location(
                self.account_ctx.paco_ref,
                self.aws_region,
            )

    def init_stage_action_codebuild_build(self, action_config):
        if not action_config.is_enabled():
            return

        self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s}'" % (action_config.paco_ref + '.project_role.arn'))
        self.kms_crypto_principle_list.append("paco.sub '${%s}'" % (action_config.paco_ref+'.project_role.arn'))

        stack_hooks = None
        if action_config.release_phase != None and len(action_config.release_phase.ecs) > 0:
            stack_hooks = StackHooks()
            stack_hooks.add(
                name='CodeBuild.ECSReleasePhase',
                stack_action='create',
                stack_timing='post',
                hook_method=self.stack_hook_codebuild_ecs_release_phase,
                cache_method=self.stack_hook_codebuild_ecs_release_phase_cache_id,
                hook_arg=action_config
            )
            stack_hooks.add(
                name='CodeBuild.ECSReleasePhase',
                stack_action='update',
                stack_timing='post',
                hook_method=self.stack_hook_codebuild_ecs_release_phase,
                cache_method=self.stack_hook_codebuild_ecs_release_phase_cache_id,
                hook_arg=action_config
            )
            self.codebuild_ecs_release_phase_ssm()


        action_config._stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.CodeBuild,
            account_ctx=self.pipeline_account_ctx,
            stack_tags=self.stack_tags,
            stack_hooks=stack_hooks,
            extra_context={
                'base_aws_name': self.base_aws_name,
                'app_name': self.app.name,
                'action_config': action_config,
                'artifacts_bucket_name': self.artifacts_bucket_meta['name'],
            }
        )

    def init_stage_action_manualapproval(self, action_config):
        pass

    def resolve_ref(self, ref):
        if schemas.IDeploymentPipelineDeployECS.providedBy(ref.resource):
            if ref.resource_ref == 'ecs-delegate.arn':
                iam_ctl = self.paco_ctx.get_controller("IAM")
                return iam_ctl.role_arn(ref.raw[:-4])
        if schemas.IDeploymentPipelineDeployS3.providedBy(ref.resource):
            if ref.resource_ref == 'delegate_role.arn':
                iam_ctl = self.paco_ctx.get_controller("IAM")
                return iam_ctl.role_arn(ref.raw[:-4])
        if schemas.IDeploymentPipelineDeployCodeDeploy.providedBy(ref.resource):
            # CodeDeploy
            if ref.resource_ref == 'deployment_group.name':
                return ref.resource._stack
            elif ref.resource_ref == 'codedeploy_tools_delegate_role.arn':
                return ref.resource._stack.template.get_tools_delegate_role_arn()
            elif ref.resource_ref == 'codedeploy_application_name':
                return ref.resource._stack.template.get_application_name()
            elif ref.resource_ref == 'deployment_group.name':
                return ref.resource._stack
        elif schemas.IDeploymentPipeline.providedBy(ref.resource):
            # DeploymentPipeline
            if ref.resource_ref.startswith('kms.'):
                return self.kms_stack
            elif ref.resource_ref.startswith('s3deploydelegate_'):
                account_name = ref.resource_ref.split('.')[0][len('s3deploydelegate_'):]
                return self.s3deploy_delegate_role_arns['paco.ref accounts.' + account_name]
            elif ref.resource_ref == 'codepipeline_role.arn':
                return ref.resource._stack.template.get_codepipeline_role_arn()
            elif ref.resource_ref == 'arn':
                return ref.resource._stack.template.pipeline_arn

        elif schemas.IDeploymentPipelineSourceCodeCommit.providedBy(ref.resource):
            # CodeCommit
            if ref.resource_ref == self.codecommit_role_name+'.arn':
                iam_ctl = self.paco_ctx.get_controller("IAM")
                return iam_ctl.role_arn(ref.raw[:-4])
            elif ref.resource_ref == 'codecommit.arn':
                codecommit_ref = ref.resource.codecommit_repository
                return self.paco_ctx.get_ref(codecommit_ref+".arn")
        elif schemas.IDeploymentPipelineSourceGitHub.providedBy(ref.resource):
            # GitHub
            if ref.resource_ref == self.github_role_name + '.arn':
                iam_ctl = self.paco_ctx.get_controller("IAM")
                return iam_ctl.role_arn(ref.raw[:-4])
        elif schemas.IDeploymentPipelineBuildCodeBuild.providedBy(ref.resource):
            # CodeBuild
            if ref.resource_ref == 'project_role.arn':
                # self.cpbd_codepipebuild_template will fail if there are two deployments
                # this application... corner case, but might happen?
                return ref.resource._stack.template.get_project_role_arn()
            elif ref.resource_ref == 'project.arn':
                # self.cpbd_codepipebuild_template will fail if there are two deployments
                # this application... corner case, but might happen?
                return ref.resource._stack.template.get_project_arn()

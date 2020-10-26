from awacs.aws import Action, Allow, Statement, Policy
from troposphere import awslambda
from paco.aws_api.awslambda.code import init_lambda_code
from paco.cftemplates.cftemplates import StackTemplate
from paco.cftemplates.eventsrule import create_event_rule_name
from paco.models.locations import get_parent_by_interface
from paco.models.loader import get_all_nodes
from paco.models.references import get_model_obj_from_ref, Reference
from paco.models import schemas
from paco.stack import StackHooks
from paco.utils import md5sum, prefixed_name
from pathlib import Path
import troposphere
import troposphere.awslambda
import troposphere.iam
import zipfile


class Lambda(StackTemplate):
    def __init__(
        self,
        stack,
        paco_ctx,
    ):
        super().__init__(
            stack,
            paco_ctx,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
        )
        account_ctx = stack.account_ctx
        aws_region = stack.aws_region
        self.set_aws_name('Lambda', self.resource_group_name, self.resource_name)
        awslambda = self.awslambda = self.stack.resource
        self.init_template('Lambda Function')

        # if not enabled finish with only empty placeholder
        if not awslambda.is_enabled(): return

        self.code_bucket_name = None

        # Parameters
        sdb_cache_param = self.create_cfn_parameter(
            name='EnableSDBCache',
            param_type='String',
            description='Boolean indicating whether an SDB Domain will be created to be used as a cache.',
            value=awslambda.sdb_cache
        )
        function_description_param = self.create_cfn_parameter(
            name='FunctionDescription',
            param_type='String',
            description='A description of the Lamdba Function.',
            value=awslambda.description
        )
        handler_param = self.create_cfn_parameter(
            name='Handler',
            param_type='String',
            description='The name of the function to call upon execution.',
            value=awslambda.handler
        )
        runtime_param = self.create_cfn_parameter(
            name='Runtime',
            param_type='String',
            description='The name of the runtime language.',
            value=awslambda.runtime
        )
        role_arn_param = self.create_cfn_parameter(
            name='RoleArn',
            param_type='String',
            description='The execution role for the Lambda Function.',
            value=awslambda.iam_role.get_arn()
        )
        role_name_param = self.create_cfn_parameter(
            name='RoleName',
            param_type='String',
            description='The execution role name for the Lambda Function.',
            value=awslambda.iam_role.resolve_ref_obj.role_name
        )
        memory_size_param = self.create_cfn_parameter(
            name='MemorySize',
            param_type='Number',
            description="The amount of memory that your function has access to. Increasing the function's" + \
            " memory also increases its CPU allocation. The default value is 128 MB. The value must be a multiple of 64 MB.",
            value=awslambda.memory_size
        )
        reserved_conc_exec_param = self.create_cfn_parameter(
            name='ReservedConcurrentExecutions',
            param_type='Number',
            description='The number of simultaneous executions to reserve for the function.',
            value=awslambda.reserved_concurrent_executions
        )
        timeout_param = self.create_cfn_parameter(
            name='Timeout',
            param_type='Number',
            description='The amount of time that Lambda allows a function to run before stopping it. ',
            value=awslambda.timeout
        )
        layers_param = self.create_cfn_parameter(
            name='Layers',
            param_type='CommaDelimitedList',
            description='List of up to 5 Lambda Layer ARNs.',
            value=','.join(awslambda.layers)
        )

        # create the Lambda resource
        cfn_export_dict = {
            'Description': troposphere.Ref(function_description_param),
            'Handler': troposphere.Ref(handler_param),
            'MemorySize': troposphere.Ref(memory_size_param),
            'Runtime': troposphere.Ref(runtime_param),
            'Role': troposphere.Ref(role_arn_param),
            'Timeout': troposphere.Ref(timeout_param),
        }
        if awslambda.reserved_concurrent_executions:
            cfn_export_dict['ReservedConcurrentExecutions'] = troposphere.Ref(reserved_conc_exec_param),

        if len(awslambda.layers) > 0:
            cfn_export_dict['Layers'] = troposphere.Ref(layers_param),

        # Lambda VPC
        if awslambda.vpc_config != None:
            vpc_security_group = self.create_cfn_ref_list_param(
                name='VpcSecurityGroupIdList',
                param_type='List<AWS::EC2::SecurityGroup::Id>',
                description='VPC Security Group Id List',
                value=awslambda.vpc_config.security_groups,
                ref_attribute='id',
            )
            # Segment SubnetList is a Segment stack Output based on availability zones
            segment_ref = awslambda.vpc_config.segments[0] + '.subnet_id_list'
            subnet_list_param = self.create_cfn_parameter(
                name='VpcSubnetIdList',
                param_type='List<AWS::EC2::Subnet::Id>',
                description='VPC Subnet Id List',
                value=segment_ref
            )
            cfn_export_dict['VpcConfig'] = {
                'SecurityGroupIds': troposphere.Ref(vpc_security_group),
                'SubnetIds': troposphere.Ref(subnet_list_param),
            }

        # Code object: S3 Bucket, inline ZipFile or deploy artifact?
        if awslambda.code.s3_bucket:
            if awslambda.code.s3_bucket.startswith('paco.ref '):
                value = awslambda.code.s3_bucket + ".name"
            else:
                value = awslambda.code.s3_bucket
            s3bucket_param = self.create_cfn_parameter(
                name='CodeS3Bucket',
                description="An Amazon S3 bucket in the same AWS Region as your function. The bucket can be in a different AWS account.",
                param_type='String',
                value=value
            )
            s3key_param = self.create_cfn_parameter(
                name='CodeS3Key',
                description="The Amazon S3 key of the deployment package.",
                param_type='String',
                value=awslambda.code.s3_key
            )
            cfn_export_dict['Code'] = {
                'S3Bucket': troposphere.Ref(s3bucket_param),
                'S3Key': troposphere.Ref(s3key_param),
            }
        else:
            zip_path = Path(awslambda.code.zipfile)
            if zip_path.is_file():
                if zipfile.is_zipfile(zip_path):
                    cfn_s3_code = self.prepare_s3bucket_artifact(is_zip=True)
                    cfn_export_dict['Code'] = cfn_s3_code
                else:
                    # Code is inline in CloudFormation template
                    # ToDo: make this legacy or optional behaviour and create a Zip and upload to S3 Bucket
                    cfn_export_dict['Code'] = {
                        'ZipFile': zip_path.read_text()
                    }
            elif zip_path.is_dir():
                cfn_s3_code = self.prepare_s3bucket_artifact()
                cfn_export_dict['Code'] = cfn_s3_code

        # Environment variables
        var_export = {}
        if awslambda.environment != None and awslambda.environment.variables != None:
            for var in awslambda.environment.variables:
                name = var.key.replace('_','')
                env_param = self.create_cfn_parameter(
                    name='EnvVar{}'.format(name),
                    param_type='String',
                    description='Env var for {}'.format(name),
                    value=var.value,
                )
                var_export[var.key] = troposphere.Ref(env_param)
            if awslambda.sdb_cache == True:
                var_export['SDB_CACHE_DOMAIN'] = troposphere.Ref('LambdaSDBCacheDomain')
            if len(awslambda.log_group_names) > 0:
                # Add PACO_LOG_GROUPS Environment Variable
                paco_log_groups = [
                    prefixed_name(awslambda, loggroup_name, self.paco_ctx.legacy_flag)
                    for loggroup_name in awslambda.log_group_names
                ]
                paco_log_groups_param = self.create_cfn_parameter(
                    name='EnvVariablePacoLogGroups',
                    param_type='String',
                    description='Env var for Paco Log Groups',
                    value=','.join(paco_log_groups),
                )
                var_export['PACO_LOG_GROUPS'] = troposphere.Ref(paco_log_groups_param)
        cfn_export_dict['Environment'] = { 'Variables': var_export }

        # Lambda resource
        self.awslambda_resource = troposphere.awslambda.Function.from_dict(
            'Function',
            cfn_export_dict
        )
        self.template.add_resource(self.awslambda_resource)

        # Published Version
        if self.awslambda.edge != None and self.awslambda.edge.auto_publish_version != None:
            version_name = self.create_cfn_logical_id(f"AutoPublishedVersion{self.awslambda.edge.auto_publish_version}")
            version_resource = troposphere.awslambda.Version(
                title=version_name,
                FunctionName=troposphere.Ref(self.awslambda_resource),
                Description="AutoPublished by Paco",
            )
            self.template.add_resource(version_resource)

            self.create_output(
                title='AutoPublishedFunctionVersionArn',
                value=troposphere.Ref(version_resource),
                ref=awslambda.paco_ref_parts + '.autoversion.arn',
            )
            self.create_output(
                title='AutoPublishedFunctionVersion',
                value=troposphere.GetAtt(version_resource, "Version"),
                ref=awslambda.paco_ref_parts + '.autoversion.version',
            )

        # SDB Cache with SDB Domain and SDB Domain Policy resources
        if awslambda.sdb_cache == True:
            sdb_domain_resource = troposphere.sdb.Domain(
                title='LambdaSDBCacheDomain',
                template=self.template,
                Description="Lambda Function Domain"
            )
            sdb_policy = troposphere.iam.Policy(
                title='LambdaSDBCacheDomainPolicy',
                template=self.template,
                PolicyName='SDBDomain',
                PolicyDocument=Policy(
                    Version='2012-10-17',
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[Action("sdb","*")],
                            Resource=[
                                troposphere.Sub(
                                    'arn:aws:sdb:${AWS::Region}:${AWS::AccountId}:domain/${DomainName}',
                                    DomainName=troposphere.Ref('LambdaSDBCacheDomain')
                                )
                            ],
                        )
                    ],
                    Roles=troposphere.Ref(role_arn_param)
                )
            )
            sdb_policy.DependsOn = sdb_domain_resource
            self.awslambda_resource.DependsOn = sdb_domain_resource

        # Permissions
        # SNS Topic Lambda permissions and subscription
        idx = 1
        for sns_topic_ref in awslambda.sns_topics:
            # SNS Topic Arn parameters
            param_name = 'SNSTopicArn%d' % idx
            self.create_cfn_parameter(
                name=param_name,
                param_type='String',
                description='An SNS Topic ARN to grant permission to.',
                value=sns_topic_ref + '.arn'
            )

            # Lambda permission
            troposphere.awslambda.Permission(
                title=param_name + 'Permission',
                template=self.template,
                Action="lambda:InvokeFunction",
                FunctionName=troposphere.GetAtt(self.awslambda_resource, 'Arn'),
                Principal='sns.amazonaws.com',
                SourceArn=troposphere.Ref(param_name),
            )

            # SNS Topic subscription
            sns_topic = get_model_obj_from_ref(sns_topic_ref, self.paco_ctx.project)
            troposphere.sns.SubscriptionResource(
                title=param_name + 'Subscription',
                template=self.template,
                Endpoint=troposphere.GetAtt(self.awslambda_resource, 'Arn'),
                Protocol='lambda',
                TopicArn=troposphere.Ref(param_name),
                Region=sns_topic.region_name
            )
            idx += 1

        # Lambda permissions for connected Paco resources
        app = get_parent_by_interface(awslambda, schemas.IApplication)
        for obj in get_all_nodes(app):
            # S3 Bucket notification permission(s)
            if schemas.IS3Bucket.providedBy(obj):
                seen = {}
                if hasattr(obj, 'notifications'):
                    if hasattr(obj.notifications, 'lambdas'):
                        for lambda_notif in obj.notifications.lambdas:
                            if lambda_notif.function == awslambda.paco_ref:
                                # yes, this Lambda gets notification from this S3Bucket
                                group = get_parent_by_interface(obj, schemas.IResourceGroup)
                                s3_logical_name = self.gen_cf_logical_name(group.name + obj.name, '_')
                                if s3_logical_name not in seen:
                                    troposphere.awslambda.Permission(
                                        title='S3Bucket' + s3_logical_name,
                                        template=self.template,
                                        Action="lambda:InvokeFunction",
                                        FunctionName=troposphere.GetAtt(self.awslambda_resource, 'Arn'),
                                        Principal='s3.amazonaws.com',
                                        SourceArn='arn:aws:s3:::' + obj.get_bucket_name(),
                                    )
                                    seen[s3_logical_name] = True

            # Events Rule permission(s)
            if schemas.IEventsRule.providedBy(obj):
                seen = {}
                for target in obj.targets:
                    target_ref = Reference(target.target)
                    target_ref.set_account_name(account_ctx.get_name())
                    target_ref.set_region(aws_region)
                    lambda_ref = Reference(awslambda.paco_ref)

                    if target_ref.raw == lambda_ref.raw:
                        # yes, the Events Rule has a Target that is this Lambda
                        group = get_parent_by_interface(obj, schemas.IResourceGroup)
                        eventsrule_logical_name = self.gen_cf_logical_name(group.name + obj.name, '_')
                        if eventsrule_logical_name not in seen:
                            rule_name = create_event_rule_name(obj)
                            # rule_name = self.create_cfn_logical_id("EventsRule" + obj.paco_ref)
                            # rule_name = hash_smaller(rule_name, 64)
                            source_arn = 'arn:aws:events:{}:{}:rule/{}'.format(
                                aws_region,
                                account_ctx.id,
                                rule_name
                            )
                            troposphere.awslambda.Permission(
                                title='EventsRule' + eventsrule_logical_name,
                                template=self.template,
                                Action="lambda:InvokeFunction",
                                FunctionName=troposphere.GetAtt(self.awslambda_resource, 'Arn'),
                                Principal='events.amazonaws.com',
                                SourceArn=source_arn,
                            )
                            seen[eventsrule_logical_name] = True

            # IoT Analytics permission(s)
            if schemas.IIoTAnalyticsPipeline.providedBy(obj):
                seen = {}
                for activity in obj.pipeline_activities.values():
                    if activity.activity_type == 'lambda':
                        target_ref = Reference(activity.function)
                        target_ref.set_account_name(account_ctx.get_name())
                        target_ref.set_region(aws_region)
                        lambda_ref = Reference(awslambda.paco_ref)
                        if target_ref.raw == lambda_ref.raw:
                            # yes, the IoT Analytics Lambda Activity has a ref to this Lambda
                            group = get_parent_by_interface(obj, schemas.IResourceGroup)
                            iotap_logical_name = self.gen_cf_logical_name(group.name + obj.name, '_')
                            if iotap_logical_name not in seen:
                                rule_name = create_event_rule_name(obj)
                                troposphere.awslambda.Permission(
                                    title='IoTAnalyticsPipeline' + iotap_logical_name,
                                    template=self.template,
                                    Action="lambda:InvokeFunction",
                                    FunctionName=troposphere.GetAtt(self.awslambda_resource, 'Arn'),
                                    Principal='iotanalytics.amazonaws.com',
                                )
                                seen[iotap_logical_name] = True

        # Log group(s)
        loggroup_function_name = troposphere.Join(
            '', [
                '/aws/lambda/',
                troposphere.Select(
                    6, troposphere.Split(':', troposphere.GetAtt(self.awslambda_resource, 'Arn'))
                )
            ]
        )
        loggroup_resources = []
        loggroup_resources.append(
            self.add_log_group(loggroup_function_name, 'lambda')
        )
        if len(awslambda.log_group_names) > 0:
            # Additional App-specific LogGroups
            for loggroup_name in awslambda.log_group_names:
                # Add LogGroup to the template
                prefixed_loggroup_name = prefixed_name(awslambda, loggroup_name, self.paco_ctx.legacy_flag)
                loggroup_resources.append(
                    self.add_log_group(prefixed_loggroup_name)
                )

        # LogGroup permissions
        log_group_arns = [
            troposphere.Join(':', [
                f'arn:aws:logs:{self.aws_region}:{account_ctx.id}:log-group',
                loggroup_function_name,
                '*'
            ])
        ]
        log_stream_arns = [
            troposphere.Join(':', [
                f'arn:aws:logs:{self.aws_region}:{account_ctx.id}:log-group',
                loggroup_function_name,
                'log-stream',
                '*'
            ])
        ]
        for loggroup_name in awslambda.log_group_names:
            prefixed_loggroup_name = prefixed_name(awslambda, loggroup_name, self.paco_ctx.legacy_flag)
            log_group_arns.append(
                f'arn:aws:logs:{self.aws_region}:{account_ctx.id}:log-group:{prefixed_loggroup_name}:*'
            )
            log_stream_arns.append(
                f'arn:aws:logs:{self.aws_region}:{account_ctx.id}:log-group:{prefixed_loggroup_name}:log-stream:*'
            )

        loggroup_policy_resource = troposphere.iam.ManagedPolicy(
            title='LogGroupManagedPolicy',
            PolicyDocument=Policy(
                Version='2012-10-17',
                Statement=[
                    Statement(
                        Sid='AllowLambdaModifyLogStreams',
                        Effect=Allow,
                        Action=[
                            Action("logs","CreateLogStream"),
                            Action("logs","DescribeLogStreams"),
                        ],
                        Resource=log_group_arns,
                    ),
                    Statement(
                        Sid='AllowLambdaPutLogEvents',
                        Effect=Allow,
                        Action=[
                            Action("logs","PutLogEvents"),
                        ],
                        Resource=log_stream_arns,
                    ),
                ],
            ),
            Roles=[troposphere.Ref(role_name_param)],
        )
        loggroup_policy_resource.DependsOn = loggroup_resources
        self.template.add_resource(loggroup_policy_resource)

        # Outputs
        self.create_output(
            title='FunctionName',
            value=troposphere.Ref(self.awslambda_resource),
            ref=awslambda.paco_ref_parts + '.name',
        )
        self.create_output(
            title='FunctionArn',
            value=troposphere.GetAtt(self.awslambda_resource, 'Arn'),
            ref=awslambda.paco_ref_parts + '.arn',
        )

    def prepare_s3bucket_artifact(self, is_zip=False):
        """
        Add a Hook which will prepare the Lambda Code artifact and upload to an S3 Bucket if it
        doesn't already exist.

        Add Parameters for CodeS3Bucket and CodeS3Key. The Parameter values are placeholder values that
        will be updated by the hook.
        """
        ignore_changes = True
        # always create an artifact on CREATE
        stack_hooks = StackHooks()
        stack_hooks.add(
            name='PrepLambdaCodeArtifactToS3Bucket',
            stack_action=['create',],
            stack_timing='pre',
            hook_method=self.prepare_s3bucket_artifact_hook,
            cache_method=self.prepare_s3bucket_artifact_cache,
            hook_arg=is_zip,
        )
        self.stack.add_hooks(stack_hooks)

        # only UPDATE an artifact if --auto-publish-code is true
        if self.paco_ctx.auto_publish_code == True:
            ignore_changes = False
            stack_hooks = StackHooks()
            stack_hooks.add(
                name='PrepLambdaCodeArtifactToS3Bucket',
                stack_action=['update'],
                stack_timing='pre',
                hook_method=self.prepare_s3bucket_artifact_hook,
                cache_method=self.prepare_s3bucket_artifact_cache,
                hook_arg=is_zip,
            )
            self.stack.add_hooks(stack_hooks)

        self.s3bucket_param = self.create_cfn_parameter(
            name='CodeS3Bucket',
            description="S3 Bucket for the Lambda Code artifact",
            param_type='String',
            value='',
            ignore_changes=ignore_changes,
        )
        self.s3key_param = self.create_cfn_parameter(
            name='CodeS3Key',
            description="S3 Key for the Lambda Code artifact",
            param_type='String',
            value='',
            ignore_changes=ignore_changes,
        )
        cfn_s3_code = {
            'S3Bucket': troposphere.Ref(self.s3bucket_param),
            'S3Key': troposphere.Ref(self.s3key_param),
        }
        return cfn_s3_code

    def prepare_s3bucket_artifact_hook(self, hook, is_zip):
        if self.code_bucket_name == None:
            self.prepare_s3bucket_artifact_cache(hook, is_zip)
        self.awslambda.stack.set_parameter(
            'CodeS3Bucket',
            self.code_bucket_name,
            ignore_changes=False
        )
        self.awslambda.stack.set_parameter(
            'CodeS3Key',
            self.code_artifact_name,
            ignore_changes=False
        )

    def prepare_s3bucket_artifact_cache(self, hook, is_zip):
        self.code_bucket_name, self.code_artifact_name, md5_hash = init_lambda_code(
            self.paco_ctx.paco_buckets,
            self.stack.resource,
            self.awslambda.code.zipfile,
            self.stack.account_ctx,
            self.stack.aws_region,
            is_zip=is_zip,
        )
        return md5_hash

    def add_log_group(self, loggroup_name, logical_name=None):
        "Add a LogGroup resource to the template"
        if not logical_name:
            logical_name = loggroup_name
        cfn_export_dict = {
            'LogGroupName': loggroup_name,
        }
        if not hasattr(self.awslambda, 'expire_events_after_days'):
            self.awslambda.expire_events_after_days = 'Never'

        if self.awslambda.expire_events_after_days != 'Never' and self.awslambda.expire_events_after_days != '':
            cfn_export_dict['RetentionInDays'] = int(self.awslambda.expire_events_after_days)
        loggroup_logical_id = self.create_cfn_logical_id('LogGroup' + logical_name)
        loggroup_resource = troposphere.logs.LogGroup.from_dict(
            loggroup_logical_id,
            cfn_export_dict
        )
        loggroup_resource.DependsOn = self.awslambda_resource
        self.template.add_resource(loggroup_resource)

        # LogGroup Output
        self.stack.register_stack_output_config(
            '{}.log_groups.{}.arn'.format(self.awslambda.paco_ref_parts, logical_name), loggroup_logical_id + 'Arn'
        )
        loggroup_output = troposphere.Output(
            loggroup_logical_id + 'Arn',
            Value=troposphere.GetAtt(loggroup_resource, "Arn")
        )
        self.template.add_output(loggroup_output)
        return loggroup_resource


"""

The ``paco.extend`` module contains convenience APIs to make it easier to extend Paco.
These APIs will be typically called from your custom Paco Service Controllers.
"""

from paco.models.loader import SUB_TYPES_CLASS_MAP, apply_attributes_from_config, load_yaml
from paco.models.exceptions import LoaderRegistrationError
from paco.models.references import is_ref, get_model_obj_from_ref
from paco.models.base import RegionContainer, AccountContainer
from paco.models.applications import Application
import paco.models.registry
from paco.models.schemas import get_parent_by_interface


def add_cw_alarm_hook(hook):
    """
    Customize CloudWatchAlarm with a hook that is called before the Alarms are initialized
    into CloudFormation templates.

    This is useful to add extra metadata to the CloudWatch Alarm's AlarmDescription field.
    This can be done in the hook by calling the ``add_to_alarm_description`` method of the cw_alarm
    object with a dict of extra metadata.

    .. code-block:: python

        import paco.extend

        def my_service_alarm_description_function(cw_alarm):
            slack_metadata = {'SlackChannel': 'http://my-slack-webhook.url'}
            cw_alarm.add_to_alarm_description(slack_metadata)

        paco.extend.add_cw_alarm_hook(my_service_alarm_description_function)

    """
    paco.models.registry.CW_ALARM_HOOKS.append(hook)

def override_cw_alarm_actions(hook):
    """
    Add a hook to change CloudWatch Alarm AlarmAction's to your own custom list of SNS Topics.
    This can be used to send AlarmActions to notify your own custom Lambda function instead of
    sending Alarm messages directly to the SNS Topics that Alarms are subscribed too.

    The hook is a function that accepts an ``alarm`` arguments and must return a List of paco.refs to SNS Topic ARNs.

    .. code-block:: python

        def override_alarm_actions_hook(snstopics, alarm):
            "Override normal alarm actions with the SNS Topic ARN for the custom Notification Lambda"
            return ["paco.ref service.notify...snstopic.arn"]

        paco.extend.override_cw_alarm_actions(override_alarm_actions_hook)

    """
    if paco.models.registry.CW_ALARM_ACTIONS_HOOK != None:
        raise LoaderRegistrationError(f"Only one Service can override CloudWatch Alarm Actions.")
    paco.models.registry.CW_ALARM_ACTIONS_HOOK = hook

def override_codestar_notification_rule(hook):
    """
    Add a hook to change CodeStar Notification Rule's to your own custom list of SNS Topics.
    This can be used to send notifications to notify your own custom Lambda function instead of
    sending directly to the SNS Topics that Alarms are subscribed too.

    .. code-block:: python

        def override_codestar_notification_rule(snstopics, alarm):
            "Override normal alarm actions with the SNS Topic ARN for the custom Notification Lambda"
            return ["paco.ref service.notify...snstopic.arn"]

        paco.extend.add_codestart_notification_rule_hook(override_codestar_notification_rule)

    """
    if paco.models.registry.CODESTAR_NOTIFICATION_RULE_HOOK != None:
        raise LoaderRegistrationError(f"Only one Service can override CodeStar Notification Rules.")
    paco.models.registry.CODESTAR_NOTIFICATION_RULE_HOOK = hook

def add_extend_model_hook(extend_hook):
    """
    Add a hook can extend the core Paco schemas and models.
    This hook is called first during model loading before any loading happens.

    .. code-block:: python

        from paco.models import schemas
        from paco.models.metrics import AlarmNotification
        from zope.interface import Interface, classImplements
        from zope.schema.fieldproperty import FieldProperty
        from zope import schema

        class ISlackChannelNotification(Interface):
            slack_channels = schema.List(
                title="Slack Channels",
                value_type=schema.TextLine(
                    title="Slack Channel",
                    required=False,
                ),
                required=False,
            )

        def add_slack_model_hook():
            "Add an ISlackChannelNotification schema to AlarmNotification"
            classImplements(AlarmNotification, ISlackChannelNotification)
            AlarmNotification.slack_channels = FieldProperty(ISlackChannelNotification["slack_channels"])

        paco.extend.add_extend_model_hook(add_slack_model_hook)

    """
    paco.models.registry.EXTEND_BASE_MODEL_HOOKS.append(extend_hook)

def register_model_loader(obj, fields_dict, force=False):
    """
    Register a new object to the model loader registry.

    The ``obj`` is the object to register loadable fields for.

    The ``fields_dict`` is a dictionary in the form:

    .. code-block:: python

        { '<fieldname>': ('loader_type', loader_args) }

    If an object is already registered, an error will be raised unless
    ``force=True`` is passed. Then the new registry will override any
    existing one.

    For example, to register a new ``Notification`` object with
    ``slack_channels`` and ``admins`` fields:

    .. code-block:: python

        paco.extend.register_model_loader(
            Notification, {
                'slack_channels': ('container', (SlackChannels, SlackChannel))
                'admins': ('obj_list', Administrator)
            }
        )

    """
    if force == False:
        if obj in SUB_TYPES_CLASS_MAP:
            raise LoaderRegistrationError(f"Object {obj} has already been registered with the model loader.")

    # ToDo: validate fields_dict
    SUB_TYPES_CLASS_MAP[obj] = fields_dict

def load_package_yaml(package, filename, replacements={}):
    """
    Read a YAML file from the same directory as a Python package and parse
    the YAML into Python data structures.
    """
    try:
        import importlib.resources as pkg_resources
    except ImportError:
        # Try backported to PY<37 `importlib_resources`.
        import importlib_resources as pkg_resources  # type: ignore
    yaml_contents = pkg_resources.read_text(package, filename)
    for placeholder, value in replacements.items():
        yaml_contents = yaml_contents.replace(placeholder, value)
    return load_yaml(yaml_contents)

def load_app_in_account_region(
    parent,
    account,
    region,
    app_name,
    app_config,
    project=None,
    monitor_config=None,
    read_file_path='not set',
    ):
    """
    Load an Application from config into an AccountContainer and RegionContainer.
    Account can be a paco.ref but then the Paco Project must be supplied too.
    """
    account_name = account
    if is_ref(account):
        account_name = get_model_obj_from_ref(account, project).name
    if account_name not in parent:
        account_cont = AccountContainer(account_name, parent)
        parent[account_name] = account_cont
    if region not in parent[account_name]:
        region_cont = RegionContainer(region, parent[account_name])
        parent[account_name][region] = region_cont
    app = Application(app_name, parent[account_name][region])
    parent[account_name][region][app_name] = app
    if project == None:
        project = get_parent_by_interface(parent)
    apply_attributes_from_config(
        app,
        app_config,
        lookup_config=monitor_config,
        read_file_path=read_file_path,
        resource_registry=project.resource_registry,
    )
    return app

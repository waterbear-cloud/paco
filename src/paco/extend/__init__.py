"""

The ``paco.extend`` module contains convenience APIs to make it easier to extend Paco.
These APIs will be typically called from your custom Paco Service Controllers.
"""

from paco.models.loader import SUB_TYPES_CLASS_MAP
from paco.models.exceptions import LoaderRegistrationError
import paco.models.registry


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
    if obj in SUB_TYPES_CLASS_MAP:
        raise LoaderRegistrationError(f"Object {obj} has already been registered with the model loader.")

    # ToDo: validate fields_dict
    SUB_TYPES_CLASS_MAP[obj] = fields_dict

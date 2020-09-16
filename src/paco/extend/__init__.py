from paco.cftemplates.cw_alarms import CW_ALARM_HOOKS

def add_cw_alarm_hook(hook):
    """
    Extend CloudWatch Alarms with a hook that is called before the AlarmDescription JSON
    is created. The hook is passed a CloudWatchAlarm object as an argument and is expected
    to call CloudWatchAlarm.add_to_alarm_description(dict) to add custom metadata to the
    AlarmDescription JSON.
    """
    CW_ALARM_HOOKS.append(hook)

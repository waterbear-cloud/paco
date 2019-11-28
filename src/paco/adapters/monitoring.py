from paco.models import vocabulary

class MonitoringService():
    """
    Adapts an IApplication and a dict of AWS describe_alarms response dicts
    to provide higher level monitoring information
    """

    def __init__(self, application, aws_alarm_info, alarm_prefix='CloudWatchAlarm-'):
        self.application = application
        self.aws_alarm_info = aws_alarm_info
        self.alarm_prefix = alarm_prefix

    def alerting_summary(self, group_name=None):
        """
        Returns a dict of alarms by classification
        and a count of those in an Alarm state:

        {
          'health': {'low': 2, 'critical': 0, 'total': 5},
          'performance': {'low': 3, 'critical': 1, 'total': 6},
          'security': {'low': 0, 'crtical': 0, 'total': 0}
        }
        """
        results = {}
        for name in vocabulary.alarm_classifications.keys():
            results[name] = {'low': 0, 'critical': 0, 'total': 0}

        for info in self.application.list_alarm_info(group_name):
            paco_alarm = info['alarm']
            aws_alarm = self.aws_alarm_info[self.alarm_prefix + paco_alarm.resource_name]
            results[paco_alarm.classification]['total'] += 1
            if aws_alarm['StateValue'] == 'ALARM':
                results[paco_alarm.classification][paco_alarm.severity] += 1

        return results


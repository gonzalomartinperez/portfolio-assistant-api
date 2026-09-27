import json
import logging

from app.application.telemetry import request_id


class RedactedJSON(logging.Formatter):
    def format(self, record):
        try:
            fields = json.loads(record.getMessage())
        except (ValueError, TypeError):
            # Non-structured messages cannot accidentally serialize exception text.
            fields = {'operation': 'unstructured_event'}
        fields.setdefault('request_id', request_id.get())
        fields['level'] = record.levelname.lower()
        return json.dumps(fields)


def configure():
    log = logging.getLogger('portfolio_assistant')
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(RedactedJSON())
        log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False

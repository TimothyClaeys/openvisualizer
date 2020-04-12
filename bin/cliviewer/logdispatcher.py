import logging.handlers
import re


class LogDispatcher(logging.Handler):
    ALL_LOGS = 0

    def __init__(self):
        super(LogDispatcher, self).__init__()
        self.viewer = None

    @classmethod
    def extract_mote_id(cls, msg):
        try:
            m = re.search(r'^([0-9a-zA-Z]{1,4}) .*', msg)
            if m is not None:
                return int(m.group(1), 16)
            else:
                return 0
        except ValueError:
            return 0

    def emit(self, record):
        try:
            level = record.levelname
            mote_id = LogDispatcher.extract_mote_id(record.message)
            msg = self.format(record)
            fs = "{}\n".format(msg)
            self.viewer.lpc.dispatch_log(fs, mote_id, level)
        except Exception:
            pass


logging.handlers.LogDispatcher = LogDispatcher

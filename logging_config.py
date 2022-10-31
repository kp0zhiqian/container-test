import logging
import time
import datetime
import os
import glob

# subclass of logging.Formatter
# https://stackoverflow.com/questions/25194864/python-logging-time-since-start-of-program
class RuntimeFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()

    def formatTime(self, record, datefmt=None):
        duration = datetime.datetime.utcfromtimestamp(
            record.created - self.start_time
        )
        elapsed = duration.strftime("%H:%M:%S.%f")[:-3]
        return "{}".format(elapsed)


def fmt_filter(record):
    record.lineno = f"{record.lineno})"
    record.filename = f"({record.filename}:"
    return True


def set_logging():
    logger = logging.getLogger()
    logger.handlers = []
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("./logs/debug.log", mode="w+")
    file_handler.setLevel(level=logging.DEBUG)
    file_formatter = RuntimeFormatter(
        "[%(asctime)s]%(filename)15s%(lineno)-4s -  %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_formatter = RuntimeFormatter("[%(asctime)s] -  %(message)s")
    stream_handler.setFormatter(stream_formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.addFilter(fmt_filter)

    return logger


def cleanup_old_log():
    for f in glob.glob("./logs/*.log"):
        os.remove(f)


# Clean old logs everytime we start this automation
# old logs should be stored at another place
cleanup_old_log()
logger = set_logging()

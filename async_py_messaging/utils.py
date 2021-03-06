"""
  Miscellaneous utilities that are short routines
  useful in multiple places.
"""
import sys
import os
import logging
import datetime
import time
import signal
import types
import platform

import async_init


class bcolors(object):
    """
    Simple names for highlighting colors.
    Use as:
        print (bcolors.BGGREEN +
            ('proc_collector pid: %d' % proc_collector.pid) +
            bcolors.ENDC)
    """
    BGRED = '\033[101m'
    BGGREEN = '\033[102m'
    BGBLUE = '\033[94m'
    BGGRAY = '\033[47m'
    ENDC = '\033[0m'


SIGNALS_TO_NAMES_DICT = dict((getattr(signal, n), n)
    for n in dir(signal) if n.startswith('SIG') and '_' not in n)


# The log levels get used in multiple places.
# The connection to logging gets used ONLY in logCollector.
# All the log levels in the logger must use these on the log
# collector side because the standard python logger class emits the logs.
#
# Remote loggers MUST use the routines in logComponents and use the
# keys in LOG_LEVEL to determine valid log levels.
LOG_LEVELS = {'DEBUG': logging.debug,
              'INFO': logging.info,
              'WARNING': logging.warning,
              'CMD': logging.warning,      # Pytrhon logging has no CMD!
              'ERROR': logging.error,
              'CRITICAL': logging.critical}

# Priority of logging. Used in filter routines.
# Key = priority name
# Value = index of priority
LOG_PRIORITY = {
                'DEBUG': 0,
                'INFO': 1,
                'WARNING': 2,
                'CMD': 3,       # At this level to capture all CMDs.
                'ERROR': 4,
                'CRITICAL': 5,
                }

# Key = index of priority
# Value = Name of level
LOG_PRIORITY_BY_NDX = {value: key for key, value in LOG_PRIORITY.items()}


def cycle_priority(cur_level):
    """
    Given the current log level such as WARNING,
    bump up to the next level, CMD. If at
    the top, CRITICAL, cycle to DEBUG.

    current_level = Name of the current level.

    Return: log level cycled up one level. If at
    CRITICAL, return DEBUG.
    """
    level = LOG_PRIORITY.get(cur_level, None)
    if level is None:
        return 'DEBUG'  # Bogus level name passed
    if level == LOG_PRIORITY['CRITICAL']:
        return 'DEBUG'
    return LOG_PRIORITY_BY_NDX[level + 1]


def filter_priority(initial_level):
    """
    initial_level: a string representing the log level.
    Given an initial_level, answer a list of
    log levels at and above this level.

    If the level is bogus, return all levels.
    """
    if initial_level not in LOG_PRIORITY.keys():
        return LOG_PRIORITY.keys()
    else:
        initial = LOG_PRIORITY[initial_level]
        filtered_priorities = {}
        for level, priority in LOG_PRIORITY.items():
            if priority >= initial:
                filtered_priorities[level] = priority
        return filtered_priorities


#  A log message contains a date, a log level and a payload
#  separated by the separation character.
SEPARATION_CHAR = '\t'

# The payload consists of name=value pairs separated
# by the PAYLOAD_CONNECTOR character.
PAYLOAD_CONNECTOR = ','
KEY_VALUE_SEPARATOR = '='

# ------------------------------------------------------------
# May use either a file log output or a database.
# ------------------------------------------------------------

# This may change depending on prog invocation run time flags.
APPEND_TO_LOG = True


# ============================================================
# Time conversion utilities.
# ============================================================
#
# The "start of the epoch" is defined as the start of the
# computer age == Jan 1, 1970 at 00:00 hours. The very first
# second of that decade.
#
# See: https://en.wikipedia.org/wiki/Unix_time
#
# ============================================================

# How time gets formatted
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'


def time_now():
    """
    Returns a floating point number as seconds since
    start of the epoch. This number has microseconds in it,
    but is not guaranteed to be that accurate. More likely
    the accuracy is to the nearest millisecond or so.
    The exact accuracy depends upon your system.
    How accurate do we need this value? Likely to the
    nearest tenth of a second, or even to the nearest second.
    """
    return time.time()


def time_now_ISO8601():
    """
    Return the current time in ISO 8601 format
    """
    secs_str = seconds_to_ISO8601(time_now())
    return secs_str


def seconds_to_ISO8601(seconds):
    """
    Given time in seconds, return an ISO 8601 string
    representation of that time.
    """
    timeDT = datetime.datetime.fromtimestamp(seconds)
    return timeDT.strftime(TIME_FORMAT)


def ISO8601_to_seconds(iso8601):
    """
    Given an ISO 8601 string in our format,
    convert to seconds.
    """
    try:
        iso_tuple = datetime.datetime.strptime(iso8601, TIME_FORMAT)
        seconds = time.mktime(iso_tuple.timetuple()) + \
                iso_tuple.microsecond/1000000.0
    except ValueError as err:
        sys.stderr.write('%s: %s\n' % (str(err), str(iso8601)))
        return None

    return seconds


def InvalidBooleanString(Exception):
    pass

def bool_value_to_bool(text_str):
    """
    Given a possible text_str, return the bool value.
    This permits such shorthands to be True/False as:
        True False Yes No T F 1 0
    """
    if isinstance(text_str, types.BooleanType):
        return text_str # Nothing to do
    text_str_upper = text_str.upper()
    if text_str in ['TRUE', 'T', '1', 'YES', 'Y']:
        return True
    if text_str in ['False', 'F', '0', 'No', 'N']:
        return False
    raise InvalidBooleanString('Invalid boolean string: %s' % text_str)


def load_config(config={}, config_filename=None):
    """

     Read the config file if any. Look in the current
     directory for the default.
     If not there, look in $HOME for the default config file.

     Default values in config may become overridden by
     the user config file. Set these befor calling.

     When config gets passed in, values not supplied by
     the input files will NOT become overwritten.

     Any user flags will override config file settings.

     Apply user flags AFTER calling this routine.

     The sequence is then:
        config = { name=value, ...  User defaults ... }
        config = load_config(config, <config_filename>)
        config = getopt() # Overrrides for runtime flags

    """
    def parse_config(file_handle):
        """
        Got a config file_handle, load it into the config.
        """
        config_lines = file_handle.read()
        config_params = eval(config_lines)
        return config_params

    def try_to_load_config(filename, config):
        try:
            file_handle = open(filename, 'r')
        except IOError:
            return None
        if file_handle:
            local_config = parse_config(file_handle)
            # Copy key=value to input config
            for key, value in local_config.items():
                config[key] = value
            return config


    dir_config = None
    home_config = None
    if config_filename is None:
        config_filename = async_init.DEFAULT_ASYNC_CONFIG_FILE
        dir_config = './' + config_filename
        home_config = os.getenv('HOME') + '/' + config_filename
    else:
        # User provided config filename.
        param_dict = try_to_load_config(config_filename, config)
        return param_dict

    param_dict = try_to_load_config(dir_config, config)
    if param_dict is not None:
        return param_dict

    param_dict = try_to_load_config(home_config)
    return param_dict


def demand_int(value):
    """
    Return a valid int.
    An invalid value results in an exception.
    """
    if isinstance(value, types.IntType):
        # Already have a value, exit
        return value

    # Insist value can convert to int
    try:
        value_int = int(value)
    except ValueError as err:
        err_msg = ('value "%s" must be an integer. %s\n' %
                (str(value), str(err)))
        sys.stder.write(err_msg)
        raise InvalidInteger(err_msg)
    return value_int


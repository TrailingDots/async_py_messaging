#!/usr/bin/env python

import os
import sys
import zmq
import signal
import atexit

import pdb

import logConfig
import apiLoggerInit
import utils
import logComponents
import log_mongo


def exiting(exit_msg):
    print('logCollector: exiting:' + exit_msg)


def signalUSR1Handler(signum, frame):
    """
    When a USR1 signal arrives, the NOISY debugging switch
    get toggled. This allows a dynamic way to trace incoming
    log messages.
        kill -USR1  1234    # 1234 is the pid of logCollector.
    """
    logConfig.NOISY = not logConfig.NOISY
    print('Log tracing now %s' % ('ON' if logConfig.NOISY else 'OFF'))


def signalUSR2Handler(signum, frame):
    """
    When a USR2 signal arrives, cycle through the log levels.
    Set the logging level to the next highest level. If already
    at the highest level, cycle to the bottom.
    This allows a dynamic way to set log level while still running.
        kill -USR2  1234    # 1234 is the pid of logCollector.
    """
    logConfig.LOG_LEVEL = utils.cycle_priority(logConfig.LOG_LEVEL)
    print('Log level set to %s' % logConfig.LOG_LEVEL)


class LogCollectorTask(object):
    """
    LogCollectorTask. One and only one instance of this
    class should exist. The LogCollectorTask collects logs
    from the logging client task.
    """
    def __init__(self, context, id_name, config):
        self.id_name = id_name
        self.context = context
        apiLoggerInit.loggerInit()
        self.frontend = self.context.socket(zmq.ROUTER)
        self.config = config
        self.mongo_client = log_mongo.LogMongo(self.config)

    def signal_handler(self, signum, frame):
        sys.stderr.write("logCollector terminated by signal %s" %
                utils.SIGNALS_TO_NAMES_DICT[signum])
        self.frontend.close()
        self.context.term()
        sys.exit(1)

    def signal_usr1_handler(self, signum, frame):
        print 'custom usr1 handler, signum:"%s"' % signum
        logConfig.NOISY = not logConfig.NOISY

    def run(self):
        """
        SIGINT and SIGTERM kill the process.
        SIGUSR1 toggles the NOISY debug of incoming logs.
        SIGUSR1 toggles the log level of incoming logs.
            Logs below the current level get discarded.

        kill -USR1 1234 # "1234" is pid of this process.
        """
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGUSR1, signalUSR1Handler)
        signal.signal(signal.SIGUSR2, signalUSR2Handler)

        try:
            self.frontend.bind('tcp://*:%s' %
                    str(logConfig.get_logging_port()))
        except zmq.ZMQError as err:
            sys.stderr.write('ZMQError: %s\n' % err)
            sys.stderr.write('Please kill other instances of this program.\n')
            sys.stderr.write('Or: another program may be using port %s\n' %
                    str(logConfig.get_logging_port()))
            sys.exit(1)

        while True:
            try:
                # ident, msg = self.frontend.recv_multipart()
                msgs = self.frontend.recv_multipart()
                ident, msg = msgs[:2]

            except KeyboardInterrupt as err:
                sys.stderr.write('Keyboard interrupt\n')
                print 'ident:%s, msg:%s' % (str(ident), str(msg))
                exiting('keyboard interrupt')
            except Exception as err:
                sys.stderr.write('Exception: %s\n' % str(err))
                exiting('exception')

            msg += utils.PAYLOAD_CONNECTOR + \
                    ('host=%s' % ident)   # Track by hostname as well
            if logConfig.NOISY:           # User has requested echo to console?
                print msg
            log_comp = logComponents.LogComponents.msg_to_components(msg)

            # Command to perform orderly exit
            if '@EXIT' in log_comp.payload:
                break

            if log_comp.level in utils.LOG_LEVELS:
                # Don't log if level is too low compared to requested level.
                if log_comp.level not in utils.filter_priority(logConfig.LOG_LEVEL):
                    continue

                if self.config['mongo']:
                    # MongoDB logging. This MUST be in a CSV format
                    # so it gets converted to JSON.
                    self.mongo_client.log2mongo(ident, log_comp)

                if self.config['text']:
                    # Text logging
                    log_fcn = utils.LOG_LEVELS[log_comp.level]
                    log_fcn(log_comp.payload)

        # This code stops with @EXIT, SIGINT or SIGTERM.
        self.frontend.close()
        self.context.term()


def load_config(config_filename=None):
    """
     Read the config file is any. Look in the current
     directory for .logcollectorrc .
     If not there, look in $HOME/.logcollectorrc
     Any user flags will override config file settings.
    """
    def parse_config(file_handle):
        # Got a config file. Load and return
        config_lines = file_handle.read()
        config_params = eval(config_lines)
        return config_params

    def try_to_load_config(filename):
        try:
            file_handle = open(filename, 'r')
        except IOError:
            return None
        if file_handle:
            return parse_config(file_handle)

    dir_config = None
    home_config = None
    if config_filename is None:
        config_filename = apiLoggerInit.DEFAULT_COLLECTOR_CONFIG_FILE
        dir_config = './' + config_filename
        home_config = os.getenv('HOME') + '/' + config_filename
    else:
        # User provided config filename.
        param_dict = try_to_load_config(config_filename)
        return param_dict

    param_dict = try_to_load_config(dir_config)
    if param_dict is not None:
        return param_dict

    param_dict = try_to_load_config(home_config)
    return param_dict


def load_config_file(config_filename):
    """
    User has requested a specific configuration filename to be loaded.
    """
    return load_config(config_filename)


def usage(msg = ''):
    if msg != None:
        print msg
    print 'logCollector [--log-file=logFilename] [port=<port#>] [-a] [-t]'
    print '     [--noisy] [--config=<config-filename>] '
    print '     [--format=JSON/TEXT]'
    print '     [--mongo=<True/False>'
    print '     [--mongo-database=<db_name>'
    print '     [--mongo-port=<mongo port>'
    print '     [--mongo-host=<mongo host>'
    print ''
    print '     --log-file=logFilename = name of file to place logs'
    print '         The default file if logs.log in the current dir'
    print '     --port=<port#> = port to listen for incoming logs'
    print '     --noisy  = Logs echo to stdout. Normally not echoed.'
    print '     --config=<config filename> - Name of config file.'
    print '         Default: local dir, then $HOME.'
    print '         Default config filename ./.logcollectorrc then $HOME/.logcollectorrc'
    print '     -a  Logs will be appended to logFilename. Default is append'
    print '     -t  logFilename will be truncated before writing logs.'
    print '     --format JSON|TEXT - what format? Default: TEXT. Also JSON available.'
    print '     --mongo=<True/False> - True = use MongoDB, False = do NOT use MongoDB'
    print '         If False, ignore all other MongoDB settings.'
    print '     --mongo-database=db_name - Name of DB in Mongo to store logs'
    print '         MongoDB will store logs.'
    print '         Default: "logs" meaning MongoDB will use a database names "logs".'
    print '     --mongo-port=<mongo daemon portrt> - Port of mongo daemon.'
    print '     --mongo-host=<mongo daemon hostname> - host name of mongo daemon.'
    print '         Default: localhost'
    print ''
    print '-a and -t apply only when --file specifics a valid filename.'
    print '--noisy or -n : Echo message to console. Useful for debugging.'
    print ''
    print 'If logFilename does not exist, it will be created.'
    print 'If logFilename does exist, by default, logs get appended.'
    print ''
    print 'logCollector --help'
    print 'logCollector -h'
    print '     This message'
    print ''
    print 'To toggle "noisy" printing of messages received:'
    print '    kill -USR1 <pid>'
    print ''
    print 'To cycle through levels of messages retained:'
    print '    kill -USR2 <pid>'
    print ''
    print 'Default configuration filename: .logcolectorrc'
    print 'Config file: Look in local dir, then $HOME.'
    print """Sample configuration file:
cat .logcollectorrc
{
    "append":   True,           # Append to existing DB and/or <log_file>
    "format":   "JSON",         # Format of logs is JSON, else Text
    "text":     True,           # True to write to <log_file>
    "log_file": './logs.log',   # Name of text file output
    "noisy":    False,          # If true, logs echoed to stdout.
    "port":     5570,           # ZeroMQ logging port 
    "mongo":    False,          # Do not use MongoDb. Ignore other Mongo settings.
    "mongo_database":  "logs",  # MongoDB database name
    "mongo_port": 27017,        # Mongodb daemon port
    "mongo_host": "localhost"   # Mongodb daemon hostname.
}
    """
    sys.exit(1)


def main():
    """main function"""
    import getopt

    print '%s: pid %d, port %s' % (' '.join(sys.argv), 
            os.getpid(), str(logConfig.PORT))

    atexit.register(exiting, 'Exiting logCollector')

    try:
        opts, args = getopt.gnu_getopt(
            sys.argv[1:], 'ahnqt',
            ['log-file=',   # output file instead of stdiout
             'port=',       # Port to listen for msgs. Default in logConfig.
             'config=',     # Config filename to load.
             'noisy',       # Noisy - messages printed to console as well as on a file.
             'append=',     # Append or not. Default: True == append
             'quiet',       # NOT Noisy - messages not printed to console
             'trunc',       # Log file to be truncated
             'format=',     # Format of data: JSON or Text
             'text',        # Write text to logs
             'mongo',       # Use MongoDB
             'mongo-database=', # Database name for mongo.
             'mongo-port=', # Database port for mongo.
             'mongo-host=', # Database host for mongo.
             'help',        # help message
            ]
        )
    except getopt.GetoptError as err:
        print err
        usage()

    # Read the config file if any. Look in the current
    # directory for .logcollectorrc .
    # If not there, look in $HOME/.logcollectorrc
    # Any user flags will override config file settings.
    config_dict = load_config()

    if config_dict is None:
        config_dict = {
            "append": True,          # Append logs to existing log file
            "log-file": 'logs.log',  # Name of log file (could be absolute filename)
            "port": 5570,            # Port to receive logs
            "noisy": False,          # Silent. Toggle with Ctrl-D
            "format": "TEXT",        # TEXT or JSON formatted logs.
            "text": False,           # True to write text logs
            "mongo": False,          # Name of MongoDB database
            "mongo_database": 'logs',# Name of MongoDB database
            "mongo_port": 27017,     # MongoDB Daemon default port
            "mongo_host": "localhost", # MongoDB hostname
        }

    return_dict = {}        # User provided config dict - if any.
    for opt, arg in opts:
        if opt in ['-h', '--help']:
            usage()
        elif opt in ['-a', '--append']:
            config_dict['append'] = arg
            continue
        elif opt in ['-n', '--noisy']:
            config_dict['noisy'] = True
            continue
        elif opt in ['-q', '--quiet']:
            config_dict['noisy'] = False
            continue
        elif opt in ['-t', '--trunc']:
            config_dict['append'] = False
            continue
        elif opt in ['--log-file']:
            config_dict['log_file'] = arg
            continue
        elif opt in ['--format']:
            config_dict['format'] = arg.upper()  # JSON or TEXT
            continue
        elif opt in ['--mongo']:
            config_dict['mongo'] = True
            continue
        elif opt in ['--mongo-database']:
            config_dict['mongo_database'] = arg
            continue
        elif opt in ['--text']:
            config_dict['text'] = True
            continue
        elif opt in ['--port']:
            try:
                port = int(arg)
            except ValueError as err:
                sys.stderr.write('Logging Port must be numeric: %s\n' % str(err))
                usage()
            config_dict['port'] = port
            continue
        elif opt in ['--mongo-port']:
            try:
                port = int(arg)
            except ValueError as err:
                sys.stderr.write('Mongo Port must be numeric: %s\n' % str(err))
                usage()
            config_dict['mongo_port'] = port
            continue
        elif opt in ['--config']:
            return_dict = load_config_file(arg)
            if not return_dict:
                usage()
            # Set whatever values read from config file.
            # If none provided, use the defaults.
            try:
                abool = utils.bool_value_to_bool(return_dict.get(config_dict['append'], False))
                config_dict['append']     = abool
            except Exception as err:
                print str(err)
                sys.exit(1)

            config_dict['log_file'] = return_dict.get('log_file', config_dict['log_file'])
            config_dict['port']     = return_dict.get('port', config_dict['port'])
            config_dict['noisy']    = return_dict.get('noisy', config_dict['noisy'])

            config_dict['format']   = return_dict.get('format', config_dict['format']).upper()
            if not (config_dict['format'] == 'JSON' or config_dict['format'] == 'TEXT'):
                usage('"format" must be either "JSON" or "TEXT"')

            try:
                abool = utils.bool_value_to_bool(return_dict.get(config_dict['noisy'], False))
                config_dict['noisy']     = abool
            except Exception as err:
                print str(err)
                sys.exit(1)

            try:
                abool = utils.bool_value_to_bool(return_dict.get(config_dict['text'], False))
                config_dict['text']     = abool
            except Exception as err:
                print str(err)
                sys.exit(1)

            try:
                abool = utils.bool_value_to_bool(return_dict.get(config_dict['mongo'], False))
                config_dict['mongo']    = abool
            except Exception as err:
                print str(err)
                sys.exit(1)

            config_dict['mongo_port'] = return_dict.get('mongo_port', config_dict['mongo_port'])

            config_dict['mongo_database'] = \
                    return_dict.get('mongo_database', config_dict['mongo_database'])
            continue
        else:
            print 'Unknown option:' + opt
            usage()
            continue

    id_name = ''
    if len(sys.argv) > 0:
        id_name = sys.argv[0]

    logConfig.APPEND_TO_LOG     = config_dict['append']
    logConfig.LOG_FILENAME      = config_dict['log_file']
    logConfig.NOISY             = config_dict['noisy']
    logConfig.PORT              = config_dict['port']
    logConfig.FORMAT            = config_dict['format']
    logConfig.TEXT              = config_dict['text']
    logConfig.MONGO             = config_dict['mongo']
    logConfig.MONGO_DATABASE    = config_dict['mongo_database']
    logConfig.MONGO_PORT        = config_dict['mongo_port']
    logConfig.MONGO_HOST        = config_dict['mongo_host']


    context = zmq.Context()
    server = LogCollectorTask(context, id_name, config_dict)
    server.run()


if __name__ == "__main__":
    main()

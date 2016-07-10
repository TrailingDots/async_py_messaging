import sys
import os

def load_config(config, filename = 'async.conf'):
    try:
        try:
            conf_fh = open(filename, 'r')
        except IOError as err:
            sys.stderr.write('IOError:%s on %s' %
                    (str(err), filename))
            sys.exit(1)
        config_lines = conf_fh.read()
        # Evaluate the contents of the config file
        params = eval(config_lines)
    except Exception as err:
        sys.stderr.write(str(err))
        sys.exit(1)

    # Copy items from conf if and only if
    # they have not been set by the caller.
    for key, value in params.items():
        if key in config:
            continue
        config[key] = value
    return config


#!/bin/env python
import zmq
import sys
import os
import signal
import async_server_create_class
from random import randint
import time
import debug

import pdb

import utils
import async_init

signal.signal(signal.SIGINT, signal.SIG_DFL)
signal.signal(signal.SIGTERM, signal.SIG_DFL)


def handle_request(ident, msg):
    """
    Handler for incoming messages.
    This processes the client message and forms
    a response. In this test case, the response
    mostly echos the request.
    ident must *not* be changed.
    msg may become transformed into whatever.
    """
    #time.sleep(randint(0, 4))
    time.sleep(randint(0, 1))
    return ident, msg + '_resp'


def usage():
    """Print the usage blurb and exit."""
    print 'server_create_class.py [--help] [--port] \\'
    print '\t\t[--noisy]'
    print '\t--help         = This blurb'
    print '\t--port=aport   = Port to expect queries.'
    print '\t--num-workers=#   = Numbers of workers.'
    print '\t--noisy        = Noisy reporting. Echo progress.'
    print ''
    sys.exit(1)


def getopts(config):
    """
        Read runtime options. Override defaults as necessary.
    """
    import getopt
    try:
        opts, args = getopt.gnu_getopt(
                sys.argv[1:], '',
                ['port=',       # Port to expect messages
                 'num-workers=', # Number of workers to process data
                 'noisy',       # If present, noisy trail for debug
                 'help',        # Help blurb
                ])
    except getopt.GetoptError as err:
        sys.stdout.write(str(err) + '\n')
        usage()

    for opt, arg in opts:
        if opt in ['--help']:
            usage()
        elif opt in ['--noisy']:
            config['noisy'] = True
            continue
        elif opt in ['--port']:
            try:
                # Insist on a valid integer for a port #
                _ = int(arg)
            except ValueError as err:
                sys.stdout.write(str(err) + '\n')
                usage()
            config['port'] = arg
            continue

        elif opt in ['--num-workers']:
            try:
                # Insist on a valid integer for a port #
                _ = int(arg)
            except ValueError as err:
                err_msg = 'Number workers: "%s", %s\n' % \
                        (str(opt), str(err))
                sys.stdout.write(err_msg)
                usage()
            config['num_workers'] = arg
            continue

    return config


def main():
    """main function"""
    import platform
    config = {
        'scheme': 'tcp',
        'port': async_init.DEFAULT_ASYNC_PORT,
        'num_workers': 5,
        'message_timeout_check': 100,   # Max # message load before timeout checks
        'in_fcn': handle_request,       # Users MUST supply this!
        'id_name': platform.node(),
        'noisy': False,                 # True to echo msgs to console. Use in debugging.
    }

    config = utils.load_config(config)
    config = getopts(config)

    server = async_server_create_class.AsyncServerCreateClass(config)
    server.start()

    server.join()

    return 0

if __name__ == "__main__":
    print '%s, pid: %d' % (' '.join(sys.argv), os.getpid())
    debug.listen()      # Create trap for infinite loops with USR1
    sys.exit(main())

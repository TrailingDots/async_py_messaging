#!/usr/binenv python
#
# Class that creates clients to send
# async messages and async receive a response.
#
# To run this test, open two windows.
# In both, got the the async_py_messaging/async_py_messaging
# directory.
#
# Start the server in one window:
#   python async_server_create_test.py
# In the other window, start the client with
# a timing loop:
#   python async_client_create_test.py --timing
#
# Toward the end of the output, the messages
# will be similar to:
#    All msgs recv. Size sent_msg_ndx: 0
#    100 logs, elapsed time: 5.014890
#    Timed at 19 messages per second
#    100 logs, elapsed time: 5.014890
#    19 messages per second
#
# The message ids will be in a "random" order
# because the "load" gets created by sleeping
# a random time.
#

import sys
import os
import platform
import time

import debug
import async_client_create_class

import pdb

# Default port
PORT = 5590


def usage():
    """Print the usage blurb and exit."""
    print 'client_create_test.py [--help] [--port]'
    print '\t--help         = This blurb'
    print '\t--port=aport   = Port to expect queries.'
    print '\t--node=anode   = Node name or IP address of server_create_class.'
    print '\t\tDefault is localhost'
    print '\t--timing       = Run timing loop only.'
    print '\targ1 ...       = Arbitrary message string'
    print ''
    sys.exit(1)


def getopts(config):
    """
    Read runtime options. Override defaults as necessary.
    """
    import getopt
    try:
        opts, _ = getopt.gnu_getopt(
            sys.argv[1:], '',
            ['port=',       # Port to expect messages
             'node=',       # Node name of server_create_class.
             'timing',      # Run timing loop only
             'help',        # Help blurb
            ])
    except getopt.GetoptError as err:
        print str(err)
        usage()

    # Number of loading args to shift out
    shift_out = 0
    for opt, arg in opts:
        if opt in ['--help']:
            usage()
        elif opt in ['--port']:
            try:
                # Insist on a valid integer for a port #
                _ = int(arg)
            except ValueError as err:
                sys.stdout.write(str(err) + '\n')
                usage()
            config['port'] = arg
            shift_out += 1
            continue
        elif opt in ['--node']:
            config['node'] = arg
            shift_out += 1
            continue
        elif opt in ['--timing']:
            config['timing'] = True
            shift_out += 1
            continue

    # Create a message out of remaining args
    for ndx in range(shift_out):
        del sys.argv[1]
    config['message'] = ' '.join(sys.argv[1:])

    return config


def do_timings(client):
    """
    Perform timings test
    """
    import timeit
    from time import time
    iterations = 100     # send/recv this many messages
    start_time = timeit.default_timer()
    for ndx in range(1, iterations):
        ndx_str = str(ndx)
        data = 'ndx=%s' % ndx_str
        client.send_multipart([ndx_str, data])
        client.sent_msg_id[ndx_str] = time()
        #print 'sent msg id ' + ndx_str
        response = client.do_poll()
        if response is not None:
            response_ndx, response_data = response
            sys.stdout.write('len(sent_msg_id): %d, response: %s\n' %
                (len(client.sent_msg_id), str(response)))
            del client.sent_msg_id[response_ndx]

    # Wait for the remainder of messages.
    # The server may not have had time to process all of them.
    print 'All msgs sent. Size sent_msg_ndx: %d' % len(client.sent_msg_id)
    # For debugging, keep track of responses
    response_list = []
    while len(client.sent_msg_id) > 0:
        response = client.do_poll()
        if response is not None:
            response_id, response_data = response
            print 'id: %s, data: %s' % (response_id, response_data)
            response_list.append(response_id)
            if response_id not in client.sent_msg_id:
                print 'Key error: ' % response_id
                pdb.set_trace()
            del client.sent_msg_id[response_id]

    print 'All msgs recv. Size sent_msg_ndx: %d' % len(client.sent_msg_id)
    elapsed = timeit.default_timer() - start_time
    sys.stdout.write('%d logs, elapsed time: %f\n' % (iterations, elapsed))
    sys.stdout.write('Timed at %d messages per second\n' %
            int(iterations/elapsed))
    print '%d logs, elapsed time: %f' % (iterations, elapsed)
    print '%d messages per second' % int(iterations/elapsed)


def main():
    """
    Dummy mainline for simple testing.
    Simply send strings, print responses

    This driver *must* be used with server_create_class.py
    because the responses have been wired in and the
    code below checks for responses.
    """

    # =========================
    # Standard initializations
    # =========================
    port = 5590

    # Default values for configuration
    config = getopts({
        'node': 'localhost',
        'port': port,
        'timing': False,
        'id_name': platform.node(),
        'message': '',
    })
    client = async_client_create_class.AsyncClientCreateClass(config)
    if client is None:
        sys.stderr.write('Cannot create ClientClass!\n')
        sys.exit(1)
    config = client.config
    client.start()

    sys.stdout.write('Started client, pid %d port %s node %s\n' %
            (os.getpid(), str(config['port']), config['node']))

    if config['timing']:
        do_timings(client)
    else:
        response = client.send_multipart(['999999', config['message']])
        sys.stdout.write(str(response) + '\n')

    client.join()
    return 0

if __name__ == '__main__':
    print '%s, pid: %d' % (' '.join(sys.argv), os.getpid())
    debug.listen()  # For interrupting infinite loops with USR1
    sys.exit(main())


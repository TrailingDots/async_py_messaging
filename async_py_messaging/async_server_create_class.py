import sys
import os
import threading
import time
import types
import signal
import zmq

import pdb

import utils

# Default port for receiving/sending messages.
DEFAULT_PORT = 5590


class AsyncServerCreateClass(threading.Thread):
    """
    Create an asynchronous server class that receives requests and
    provides for sending server responses.
    Modeled after asyncsrv.py in the ZeroMQ zguide.
    """

    def __init__(self, config):
        """
        config as a dictionary describes the client configuration.
        All but id_name keywords are required.

        id_name = These names appear in the log entry as
            an identifier of the source
            of the log entry.

        port = port to use for communications.

        num_workers = The number of workers to create.
            A worker reads incoming messages,
            calls the user specified routine and
            passes the result of that routine
            back to the caller.
        """

        super(AsyncServerCreateClass, self).__init__()
        self.config = config
        self.workers = []   # Thread list of workers.
        self.is_noisy = self.config.get('noisy', False)


    def run(self):
        global DEFAULT_PORT
        context = zmq.Context()
        frontend = context.socket(zmq.ROUTER)
        port = utils.demand_int(self.config.get('port', DEFAULT_PORT))
        scheme = self.config.get('scheme', 'tcp')
        endpoint = '%s://*:%s' % (scheme, str(port))
        sys.stdout.write('endpoint: "%s" noisy=%s\n' % 
                (endpoint, self.is_noisy))

        try:
            frontend.bind(endpoint)
        except zmq.ZMQError as err:
            # Common problem: someone else using this port.
            sys.stderr.write('frontend endpoint: %s: %s\n' %
                    (endpoint, str(err)))
            frontend.close()
            context.term()
            os.kill(os.getpid(), signal.SIGINT)

        backend = context.socket(zmq.DEALER)
        try:
            backend.bind('inproc://backend')
        except zmq.ZMQError as err:
            # Common problem: someone else using this port.
            sys.stderr.write('backend Port %s: %s\n' %
                    (self.config['port'], str(err)))
            frontend.close()
            backend.close()
            context.term()
            os.kill(os.getpid(), signal.SIGINT)

        self.config['context'] = context

        # Spawn some worker threads
        #for _ in range(utils.demand_int(self.config.get('num_workers', 5))):
        for worker_ndx in range(3):
            worker = AsyncServerWorker(self.config, worker_ndx)
            worker.start()
            self.workers.append(worker)

        zmq.proxy(frontend, backend)

        frontend.close()
        backend.close()
        context.term()


class ExitException(Exception):
    """Exception that indicates an exit."""
    pass

# All threads use this flag to determine an exit condition.
is_alive = True


class AsyncServerWorker(threading.Thread):
    """
    AsyncServerWorker
    Each individual worker waits for a messages,
    calls the user specified routine to process the
    messages, and sends a reply to the caller.

    The architecture of ROUTER/DEALER in ZeroMQ
    ensures workers receive messages in a round-robin
    manner.

    To cleanly shut down workers with a @EXIT command
    from an external source, create a PUB/SUB that
    send the kill command to _all_ workers created.
    The worker that received the kill then publishes
    the kill to all other workers. Each worker SUBs
    to the PUB.
    The port number for this is one greater than the
    worker pub.
    """

    def __init__(self, config, worker_ndx):
        super(AsyncServerWorker, self).__init__()

        self.context = config['context']
        self.config = config
        self.is_noisy = self.config.get('noisy', False)
        self.control_pub = None
        self.control_sub = None
        self.worker_ndx = worker_ndx

    def run(self):
        worker = self.context.socket(zmq.DEALER)
        worker.connect('inproc://backend')

        scheme = self.config.get('scheme', 'tcp')
        self.control_pub = self.context.socket(zmq.PUB)
        endpoint = 'inproc://control%d' % self.worker_ndx

        try:
            self.control_pub.bind(endpoint)
        except zmq.ZMQError as err:
            # Common problem: someone else using this port.
            sys.stderr.write('control bind endpoint: %s: %s\n' %
                    (endpoint, str(err)))
            self.control_pub.close()
            self.context.term()
            os.kill(os.getpid(), signal.SIGINT)

        # Create a subscriber to the publisher.
        # Multiple workers need to listen to control
        self.control_sub = self.context.socket(zmq.SUB)
        try:
            self.control_sub.connect(endpoint)
        except zmq.ZMQError as err:
            sys.stderr.write('control connect endpoint: %s: %s\n' %
                    (endpoint, str(err)))
            self.control_pub.close()
            self.context.term()
            os.kill(os.getpid(), signal.SIGINT)

        poller = zmq.Poller()
        poller.register(self.control_sub, zmq.POLLIN)
        poller.register(worker, zmq.POLLIN)

        while True:
            event = poller.poll()   # Wait for a message
            try:
                alist = event[0][0].recv_multipart()
                ident, msg_id, msg = alist
            except ValueError as err:
                print str(err)
                import pdb; pdb.set_trace()

            if self.is_noisy: 
                print 'recv ident: %s msg_id:%s msg: %s' %(ident, str(msg_id), msg)
            if '@EXIT' in msg:
                #import pdb; pdb.set_trace()
                self.control_pub.send_multipart([ident, msg_id, '@KILL@'])
                print '@KILL@ published'
                break

            if '@KILL@' in msg:
                break

            # Call the user defined function to handle the message.
            # The user defined function returns the response to be sent
            # to the client.
            response = self.config['in_fcn'](ident, msg)
            ident, resp_msg = response
            # Echo the msg id back to the client.
            worker.send_multipart([ident, msg_id, resp_msg])
            if self.is_noisy: print 'respond ident: %s msg: %s' %(ident, resp_msg)

        worker.close()


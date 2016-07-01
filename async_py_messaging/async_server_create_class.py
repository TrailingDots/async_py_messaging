#!/bin/env python
import sys
import os
import threading
import time
import signal
import zmq


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
        """

        super(AsyncServerCreateClass, self).__init__()
        self.config = config
        self.workers = []   # Thread the workers are on.
        self.is_noisy = self.config.get('noisy', False)


    def demandIntPort(self):
        """Insist that key be in the config dict.
        Return the valid in the config dict."""
        port = self.config.get('port', 5590)

        # Insist the key is an integer
        try:
            port = int(port)
        except ValueError as err:
            sys.stdout.write('port "%s" must be an integer. %s\n' %
                    (str(port), str(err)))
            sys.exit(1)
        return port

    def run(self):
        context = zmq.Context()
        frontend = context.socket(zmq.ROUTER)
        port = self.demandIntPort()
        scheme = self.config.get('scheme', 'tcp')
        endpoint = '%s://*:%s' % (scheme, str(port))
        sys.stdout.write('endpoint: "%s" noisy=%s\n' % (endpoint, self.is_noisy))

        try:
            frontend.bind(endpoint)
        except zmq.ZMQError as err:
            # Common problem: someone using this port.
            sys.stderr.write('Port %s: %s\n' %
                    (self.config['port'], str(err)))
            frontend.close()
            context.term()
            os.kill(os.getpid(), signal.SIGINT)

        backend = context.socket(zmq.DEALER)
        backend.bind('inproc://backend')

        self.config['context'] = context

        # Spawn some worker threads
        for _ in range(20):
            worker = AsyncServerWorker(self.config)
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
    """AsyncServerWorker"""

    def __init__(self, config):
        super(AsyncServerWorker, self).__init__()

        self.context = config['context']
        self.config = config
        self.is_noisy = self.config.get('noisy', False)

    def run(self):
        global is_alive
        worker = self.context.socket(zmq.DEALER)
        worker.connect('inproc://backend')
        while is_alive:
            try:
                alist = worker.recv_multipart()
                ident, msg_id, msg = alist
            except ValueError as err:
                print str(err)
                import pdb; pdb.set_trace()
            if self.is_noisy: print 'recv ident: %s msg_id:%s msg: %s' %(ident, str(msg_id), msg)

            # Call the user defined function to handle the message.
            # The user defined function returns the response to be sent
            # to the client.
            response = self.config['in_fcn'](ident, msg)
            ident, resp_msg = response
            # Echo the msg id back to the client.
            worker.send_multipart([ident, msg_id, resp_msg])
            if self.is_noisy: print 'respond ident: %s msg: %s' %(ident, resp_msg)
            if '@EXIT' in resp_msg:
                is_alive = False
                time.sleep(1)   # Some time to send response.
                break

        worker.close()


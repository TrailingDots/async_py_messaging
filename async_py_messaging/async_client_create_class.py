#!/usr/env python
#
# Class that creates clients to send
# messages and receive a response.
#

import sys
import zmq
import threading
import traceback
import platform
import time

import pdb


class AsyncClientCreateClass(threading.Thread):
    """
    Create as asychronouw client class that sends requests and
    receives server responses.

    Once a message gets sent, it awaits a response.
    """

    def __init__(self, config):
        """
        config as a dictionary describes the client configuration.
        All but id_name keywords are required.

        id_name = These names appear in the log entry as the 
                identifier of the source of the log entry.

        port = port to use for communications.

        node = name of node. For servers, this may commonly be '*'
                For clients, this may be localhost or a node name.

        """
        self.msg_id = 0  # simple incrementing for unique msg_id

        # Keep track of msgs send but no response
        # key = msg_id string, value = timestamp of sending
        self.sent_msg_id = {}   


        def demandKey(key, default):
            """
            Insist that key be in the config dict.
            Return the valid in the config dict.
            """
            if key not in config:
                config[key] = default
            return config[key]

        try:
            self.port = int(demandKey('port', 5590))
        except ValueError as err:
            sys.stdout.write('port "%s" must be an integer. %s\n' % 
                    (str(config['port']), str(err)))
            sys.exit(1)     # No real way to recover!

        self.config = config
        self.id_name = demandKey('id_name', platform.node())
        self.scheme = 'tcp'     # udp, etc. later
        self.node = demandKey('node', 'localhost')

        self.context = None
        self.socket = None
        self.poll = None
        self.poller = None
        self.reqs = 0       # Count of message requests
        threading.Thread.__init__(self)


    def add_to_sent_msg_id(self, msg_id):
        """ Add msg_id to sent_msg_id dictionary """
        sys.stdout.write('adding sent_msg_id: %s\n' % str(msg_id))
        self.sent_msg_id[msg_id] = time.time()
        print 'sent_msg_id: %s' % str(self.sent_msg_id)



    def del_from_sent_msg_id(self, msg_id):
        """ Delete msg_id from sent_msg_id dictionary """
        try:
            print 'del of %s' % str(msg_id)
            del self.sent_msg_id[msg_id]
        except KeyError as err:
            print 'ERROR: del msg_id:%s' % str(err)
            print 'sent_msg_id: %s' % str(self.sent_msg_id)
            import pdb; pdb.set_trace()
        

    def run(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.LINGER, 0)
        identity = u'%s' % str(self.id_name)
        self.socket.identity = identity.encode('ascii')
        app_socket = '%s://%s:%d' % (self.scheme, self.node, self.port)
        try:
            self.socket.connect(app_socket)
        except zmq.ZMQError as err:
            sys.stdout.write('connect ZMQError: "%s": %s\n' % (app_socket, str(err)))
            sys.exit(1)
        except Exception as err:
            sys.stdout.write('connect Exception: %s: %s\n' % (app_socket, str(err)))
            sys.exit(1)
        sys.stdout.write('Connected: %s\n' % app_socket)

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)


    def send_multipart(self, alist):
        """
        Send alist as frames
        Contents:
        alist[0] = The message id
        alist[1] = The message payload. This may be arbitrarily
            complex.
        """
        try:
            self.socket.send_multipart(alist)
            self.add_to_sent_msg_id(alist[0])
        except zmq.ZMQError as err:
            sys.stderr.write('ERROR in send_multipart:%s\n' % err)


    def send(self, astr):
        """Send astr as a fully formed message.
        Return True  for successful send.
               False for failure.
        """
        try:
            self.socket.send_string(astr)
        except zmq.ZMQError as err:
            sys.stderr.write('ERROR in send_string:%s\n' % err)
            return 1    # Non-zero status == problems

        response = self.recv()
        return response

    def do_poll(self):
        """
        Poll for any messages.
        Return None if no messages,
        else return the message.
        """
        socks_dict = dict(self.poller.poll())

        if self.socket in socks_dict:
            if socks_dict[self.socket] == zmq.POLLIN:
                message = self.socket.recv_multipart()
                response_id, payload = message
                self.del_from_sent_msg_id(response_id)
                return message
        return None

    def recv(self):
        """Receive a message."""
        response = self.socket.recv()
        return response


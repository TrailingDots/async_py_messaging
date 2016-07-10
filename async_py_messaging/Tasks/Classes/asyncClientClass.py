
import zmq
import sys
import os
import threading
import time
from random import randint, random

def tprint(msg):
    """like print, but won't get newlines confused with multiple threads"""
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()

class ClientTask(threading.Thread):
    """ClientTask"""
    def __init__(self, id, config):
        self.id = id
        self.config = config
        self.noisy = self.config.get('noisy', False)
        threading.Thread.__init__ (self)

    def run(self):
        context = zmq.Context()
        socket = context.socket(zmq.DEALER)
        identity = u'worker-%d' % self.id
        socket.identity = identity.encode('ascii')
        socket.connect('tcp://localhost:5570')
        if self.noisy: print('%d: Client %s started' % (os.getpid(), identity))
        poll = zmq.Poller()
        poll.register(socket, zmq.POLLIN)
        reqs = 0
        while True:
            reqs = reqs + 1
            if self.noisy: print('Req #%d sent..' % (reqs))
            socket.send_string(u'request #%d' % (reqs))
            for i in range(5):
                sockets = dict(poll.poll(1000))
                if socket in sockets:
                    msg = socket.recv()
                    if self.noisy: 
                        tprint('%d: Client %s received: %s' % 
                            (os.getpid(), identity, msg))

        socket.close()
        context.term()



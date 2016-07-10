
import zmq
import sys
import threading
import time
from random import randint, random

def tprint(msg):
    """like print, but won't get newlines confused with multiple threads"""
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()


class ServerWorker(threading.Thread):
    """ServerWorker"""
    def __init__(self, context, ndx, config):
        threading.Thread.__init__ (self)
        self.context = context
        self.config = config
        self.noisy = self.config.get('noisy', False)
        self.sleep = self.config.get('sleep', False)

    def run(self):
        worker = self.context.socket(zmq.DEALER)
        worker.connect('inproc://backend')
        if self.noisy: tprint('Worker started')
        while True:
            ident, msg = worker.recv_multipart()
            if self.noisy: 
                tprint('Worker received %s from %s' % (msg, ident))
            replies = randint(0,4)
            for i in range(replies):
                if self.sleep:
                    time.sleep(1. / (randint(1,10)))
                worker.send_multipart([ident, msg])

        worker.close()



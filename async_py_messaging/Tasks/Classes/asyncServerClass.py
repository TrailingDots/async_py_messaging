
import zmq
import sys
import threading
import time
from random import randint, random

import asyncServerWorkerClass

def tprint(msg):
    """like print, but won't get newlines confused with multiple threads"""
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()


class ServerTask(threading.Thread):
    """ServerTask"""
    def __init__(self, config):
        threading.Thread.__init__ (self)
        self.config = config

    def run(self):
        context = zmq.Context()
        frontend = context.socket(zmq.ROUTER)
        frontend.bind('tcp://*:5570')

        backend = context.socket(zmq.DEALER)
        backend.bind('inproc://backend')

        workers = []
        for i in range(5):
            worker = asyncServerWorkerClass.ServerWorker(context, i, self.config)
            worker.start()
            workers.append(worker)

        zmq.proxy(frontend, backend)

        frontend.close()
        backend.close()
        context.term()




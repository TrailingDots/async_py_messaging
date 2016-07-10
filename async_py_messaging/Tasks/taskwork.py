# Ref: ZeroMQ, p. 58, taskwork2.py in zguide

import sys
import os
import time
import zmq

import pdb


class TaskWork(object):

    def __init__(self, config):
        # PUB-SUB flow that responds cleanly to a kill signal
        self.config = config
        self.context = zmq.Context()

        
        # Socket to receive messages
        self.endpoint_recv = 'tcp://localhost:5557'
        self.receiver = self.context.socket(zmq.PULL)
        self.receiver.connect(self.endpoint_recv)

        # Socket to send messages
        self.endpoint_to_sink = 'tcp://localhost:5558'
        self.to_sink = self.context.socket(zmq.PUSH)
        self.to_sink.connect(self.endpoint_to_sink)

        # Socket to control input
        self.controller = self.context.socket(zmq.SUB)
        self.endpoint_controller = 'tcp://localhost:5559'
        self.controller.connect(self.endpoint_controller)
        self.controller.setsockopt(zmq.SUBSCRIBE, '')

        self.poller = zmq.Poller()
        self.poller.register(self.receiver, zmq.POLLIN)
        self.poller.register(self.controller, zmq.POLLIN)


    def process_messages(self):
        """
        Process messages
        """
        while True:
            socks = dict(self.poller.poll())

            print 'socks: %s' % str(socks)

            if socks.get(self.receiver) == zmq.POLLIN:
                message = self.receiver.recv_string()

                # Process task
                print message

                # Send results to sink
                self.to_sink.send_string('work_to_sink: %s' % message)

                # Simple progress indicator for the viewer
                sys.stdout.write('.')
                sys.stdout.flush()

            # Any waiting controller command acts as 'KILL'
            if socks.get(self.controller) == zmq.POLLIN:
                message = self.controller.recv_string()
                print 'taskwork controller: %s' % message
                break

        print ' Finished taskwork'
        self.receiver.close()
        self.to_sink.close()
        self.controller.close()
        self.context.term()
        print 'all closed up'


if __name__ == '__main__':
    config = {}
    task_work = TaskWork(config)
    task_work.process_messages()

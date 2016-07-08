# Ref: ZeroMQ, p. 60
# Parallel task sink with kill signaling

import sys
import time
import zmq

import pdb

class TaskSink(object):

    def __init__(self, config):
        self.config = config
        self.context = zmq.Context()

        # Socket to receive msgs
        self.receiver = self.context.socket(zmq.PULL)
        self.endpoint_receiver = 'tcp://*:5558'
        self.receiver.bind(self.endpoint_receiver)

        # Socket for worker control
        self.controller = self.context.socket(zmq.PUB)
        self.endpoint_controller = 'tcp://*:5559'
        self.controller.bind(self.endpoint_controller)


    def process(self):

        # Wait for start of batch
        self.receiver.recv()

        # Start our clock now
        tstart = time.time()

        # Process 100 confirmations
        task_nbr = 0
        #for task_nbr in range(1, 25):
        while True:
            task_nbr += 1
            msg = self.receiver.recv()
            print str(msg)

            if str(msg) == 'KILL':
                print 'KILL received. task #%d' % task_nbr
                break

            if task_nbr % 10 == 0:
                sys.stdout.write(':')
            else:
                sys.stdout.write('.')
            sys.stdout.flush()

        # Calculate and report duration of batch
        tend = time.time()
        tdiff = tend = tstart
        total_msec = tdiff * 1000
        sys.stdout.write('\nTotal elapsed ms: %d\n' % total_msec)

        # Send kill signal to workers
        print 'sending KILL to workers'
        self.controller.send(b'KILL')

        # finished
        self.receiver.close()
        self.controller.close()
        self.context.term()

if __name__ == '__main__':
    config = {}
    task_sink = TaskSink(config)
    task_sink.process()



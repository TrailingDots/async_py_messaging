#!/bin/env python
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

        self.poller = zmq.Poller()
        self.poller.register(self.receiver, zmq.POLLIN)


    def process(self):

        # Wait for start of batch
        # Blocks until 1st msg, ignored msg.
        #msg = self.receiver.recv()
        #print 'start: %s' % str(msg)

        # Start our clock now
        tstart = time.time()

        task_nbr = 0
        while True:
            task_nbr += 1
            socks = dict(self.poller.poll())
            
            print 'sink socks:' + str(socks)

            if socks.get(self.receiver) == zmq.POLLIN:
                msg = self.receiver.recv_string()
                print str(msg)
                if 'KILL' in msg:
                    print 'sink KILL received. task #%d' % task_nbr
                    # Send to all workers.
                    self.controller.send_string('KILL')
                    time.sleep(1)   # Time to send msgs
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
        self.controller.send('KILL')

        # finished
        self.receiver.close()
        self.controller.close()
        self.context.term()

if __name__ == '__main__':
    config = {}
    task_sink = TaskSink(config)
    task_sink.process()



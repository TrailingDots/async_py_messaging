# Ref: ZeroMQ, p. 17
#
# Bind PUSH socket to port 5557
# Sends batch of tasks to workers via that socket
#
# To test this, open 4 consoles
# cd to the dir of code in each console
# Enter the following:
# console 1:  python tasksink.py
# console 2:  python taskwork.py
# console 3:  python taskwork.py
# console 4:  python taskvent.py
#
# Press ENTER when ready.
#
# The sink console will report incrementing numbers
# and then a "KILL received"
#
# The two worker consoles will report incrementing numbers.
# Typically, only one worker receives the entire load.
# Then each worker reports a KILL
#
# The vent console reports a KILL send to the sink.
#

import sys
import os
import zmq
import random
import time

class TaskVent(object):

    def __init__(self, config):
        self.config = config
        self.context = zmq.Context()

        # Socket to send messages
        self.sender = self.context.socket(zmq.PUSH)
        self.endpoint_sender = 'tcp://*:5557'
        self.sender.bind(self.endpoint_sender)

        # Socket with direct access to the sink:
        # Use to synchronize start of batc(self.endpoint_sender)

        # Socket with direct access to the sink:
        # used to synchronize start of batch
        self.sink = self.context.socket(zmq.PUSH)
        self.endpoint_sink = 'tcp://localhost:5558'
        self.sink.connect(self.endpoint_sink)

    def process(self):
        pass



if __name__ == '__main__':
    print 'Press Enter when the workers are ready'
    _ = raw_input()
    config = {}
    task_vent = TaskVent(config)

    # 1st msg is '0' indicating start of batch
    task_vent.sink.send(b'0')

    # Init random number generator
    random.seed()

    # Send 100 tasks
    total_ms = 0
    for task_nbr in range(1, 100):

        # Random workload from to 100 ms
        #workload = random.randint(1, 100)
        workload = task_nbr
        total_ms += workload

        task_vent.sender.send_string(u'%i' % workload)

    sys.stdout.write('Total expected cost: %s ms\n' % total_ms)

    # Give time to deliver
    time.sleep(1)

    task_vent.sink.send_string('KILL')
    print 'KILL msg sent to sink from vent'



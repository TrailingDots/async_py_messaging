#
# Init params for asynchronous messaging.
#
# This config file handles info for async messaging
# as well as logging.
#
# "One config file to bind them."
#

import platform
import sys
import os
import pdb

# The name of the default config file.
# The search order:
#   1. The local directory where the program was started.
#   2. The $HOME directory
#
DEFAULT_ASYNC_CONFIG_FILE = '.async_messagingrc'

# Default port number for asynchronous messaging
DEFAULT_ASYNC_PORT = 5590



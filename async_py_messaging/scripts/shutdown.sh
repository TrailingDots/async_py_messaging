#!/usr/bin/bash
#
# Shutdown the mongod gracefully.
#
mongo --quiet <<HERE >/dev/null
use admin
db.shutdownServer()
HERE
sleep 3


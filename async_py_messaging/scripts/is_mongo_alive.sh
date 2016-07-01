#!/usr/bin/bash
#
# Returns status code 0 == mongod is alive
#         else, mongod is not running
#
mongo --quiet --eval 'show dbs' >/dev/null



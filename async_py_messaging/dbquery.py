#!/bin/env python
#
#   MongoDB Command line query utility
#
# Query the mongo database with a query.
# This exists because the shell add all kinds
# of obscuring notation.
#
import pymongo
import pdb
import sys, os
import bson
from pymongo import MongoClient


def do_command(config_dict):
    client = pymongo.MongoClient(config_dict['host'], config_dict['port'])
    db = client[config_dict['db_name']]
    result = eval(config_dict['cmd'])
    return result


def print_results(results):
    if type(results) == type(1):
        print results
    elif type(results) == type(bson.objectid.ObjectId()):
        # From an insert
        print results
    elif type(results) == type({}):
        # From remove()
        print results
    else:
        for item in results:
            print str(item)


def usage():
    print """
    dbquery [--port=<mongod port> --host=<mongod host>] [--help] db_name query

        --port=<port#>  Defaults to standard mongod port of 27107

        --host=<hostname> Defaults to host of mongod of 'localhost'

        db_name = The database name

        query   = The mongodb query. Something like:
                    'db.logs.find("package.level": "CRITICAL")'

                  The command portion contains the collection name.

                  The 'db' part of the command MUST be present
                  because it gets linked to your external db_name.

                  Make sure this has single quotes and the inner
                  quotes are double quotes. The bash shell demands this
                  or the string will yield strange results.

    Sample query:
        dbquery mydb 'db.test.find({"payload.middle": "Harry"})'
    Searches the 'mydb' database for a record names 'payload'.
    That 'payload' record contains a sub-record named 'middle'
    and the specific record requred has a value of 'Harry'.

    Using a format as close as possible to the mongo shell allows
    a more egonomic interface.

    This utility does not handle such queries as 'show dbs' because
    only queries as 'db.coll.find(...)' are supported.

    Return codes:
        0 = Success. The results get printed to sys.stdout.
            If nothing gets printed, perhaps no records match
            the query. Perhaps the query was ill-formed?
        non-0 = An error message should assist in debugging
            or perhaps the query was ill-formed.
    """
    sys.exit(1)

def main():
    import getopt

    try: opts, args = getopt.gnu_getopt(
            sys.argv[1:], '',
            ['port=',       # Port mongod runs on
             'help',        # Help message
             'host=',       # host mongod runs on
            ])
    except Exception as err:
        print str(err)
        usage()

    config_dict = {
            'port': 27017,       # Default mongod port
            'host': 'localhost', # Default host name. Run locally.
        }

    for opt, arg in opts:
        if opt in ['--help']:
            usage()     # Does not return
        elif opt in ['--port']:
            config_dict['port'] = int(arg)
            continue
        elif opt in ['--host']:
            config_dict['host'] = arg
            continue
        else:
            print 'Unknown option: ' + opt
            usage()

    if len(args) != 2:
        usage()
    config_dict['db_name'] = args[0]
    config_dict['cmd'] = args[1]

    try:
        results = do_command(config_dict)
    except Exception as err:
        print str(err)
        sys.exit(1)

    print_results(results)

if __name__ == '__main__':
    main()
    sys.exit(0)
        



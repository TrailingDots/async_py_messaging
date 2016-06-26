import sys
import os
import json
import pymongo
from bson import json_util
from pymongo import MongoClient
import utils

import pdb

import logConfig
import logFilter

class LogMongo(object):
    """
    Class to handle logging to MongoDB.

    mongod must be started as:
        mongod --rest --config mongodb.conf

    mongodb.conf uses the default config file.

    The logCollector uses .logcollectorrc similar to:
{
    "append":   True,           # Append to existing DB and/or <out_file>
    "format":   "JSON",         # Format of logs is JSON, else Text
    "mongo":    True            # Mongo is running
    "mongo_database": "logs",   # MongoDB database name
    "mongo_port":  27017,       # MongoDB port
    "mongo_host":  "localhost", # Host for mongodb server
    "text":     False,           # True to write to <out_file>
    "log_file": './logs.log',   # Name of text file output
    "noisy":    False,          # If true, logs echoed to stdout.
    "port":     5570,           # ZeroMQ logging port 
}
    
    If a text file output is not desired, set   'text': False  
    While both mongodb output and text file output can offer
    complimentary results, this results in an uncommon case.
    """
    CLIENT = None
    def __init__(self, config):
        self.use_mongo = False
        self.config = config
        if not config['mongo']:
            # No Mongo database name. Mongo is NOT used.
            return
        db_name = config['mongo_database']

        # The interface to MongoDB requires a singleton
        if LogMongo.CLIENT is None:
            self.db_name = db_name
            self.collection = 'logs'    # Fixed to "logs" - for now.
            self.port = config['mongo_port']
            self.host = config['mongo_host']
            self.client = pymongo.MongoClient(self.host, self.port)
            self.database = self.client[self.db_name]

            print 'Opening MongoDB. db:%s, collections=%s, port=%s, host=%s' % \
                    (self.db_name, self.collection, self.port, self.host)

            # This ensure only a singleton instance gets created.
            LogMongo.CLIENT = self


    def log2mongo(self, ident, log_comp):
        """
        Log to MongoDB.
        """
        iso8601_time = utils.time_now_ISO8601()

        post = {'ident': ident,
                'iso8601_time': iso8601_time,
                'level': log_comp.level,
                'payload': log_comp.payload}

        if self.config['format'] == 'JSON':
            payload_dict = self.parse_payload(post['payload'])
            post['payload'] = payload_dict

        try:
            result = self.database[self.collection].insert_one(post)
        except Exception as err:
            print 'log_mongo: %s' % str(err)


    def parse_payload(self, payload):
        """
        Parse the payload.
        This routine converts the payload to a nested dictionary.
        """
        payload_dict = {}
        items = payload.split(',')
        for item in items:
            if len(item) == 0:
                # Ignore empty items.
                # An example:    name=value,,name1=value1
                # The double ',,' results in an empty item.
                continue
            try:
                if item.find('=') == -1:
                    # The item has no key=value.
                    # Fake it with a key of 'text'.
                    # This happens when logCmd sends just a
                    # non-structured comment.
                    # WARNING: A text comment with an embedded
                    # comma results in only the portion after
                    # the last comma as a valid field.
                    item = 'text=' + item
                key, value = item.split('=')
                key = key.strip()
                value = value.strip()
            except ValueError as err:
                sys.stderr.write(('ERROR: "%s", "%s" payload: "%s"\n') %
                        (str(err), item, str(payload)))
                continue    # Ignore this entry
            # Duplicate keys get ignored.
            payload_dict[key] = value
        
        return payload_dict

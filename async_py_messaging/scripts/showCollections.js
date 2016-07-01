#!/usr/bin/env node
/**
 Show collections in a MongoDB database
*/
var MongoClient = require('mongodb').MongoClient
var conn = MongoClient.connect('localhost', 27017)
var db = conn.getDB('logs')
db.logs.find().count()
console.log(db.logs.find().count());



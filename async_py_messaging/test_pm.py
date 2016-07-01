# Ref: http://api.mongodb.com/python/current/tutorial.html

import pymongo
from pymongo import MongoClient

client = MongoClient()

db = client.test_database
collection = db.test_collection

import datetime
post = {"author": "Mike",
        "text": "My first blog post!",
        "tags": ["mongodb", "python", "pymongo"],
        "date": datetime.datetime.utcnow()}

posts = db.posts
post_id = posts.insert_one(post).inserted_id
print 'post_id:' + str(post_id)

print 'collections:' + str(db.collection_names(include_system_collections=False))

item = posts.find_one()
print 'item:' + str(item)

item = posts.find_one({"author": "Mike"})
print 'item Mike:' + str(item)
new_posts = [{"author": "Mike",
               "middle": 'XXX',
               "text": "Another post!",
               "tags": ["bulk", "insert"],
               "date": datetime.datetime(2009, 11, 12, 11, 14)},
              {"author": "Eliot",
               "middle": 'him',
               "title": "MongoDB is fun",
               "text": "and pretty easy too!",
               "date": datetime.datetime(2009, 11, 10, 10, 45)}]
result = posts.insert_many(new_posts)
print '\nbulk insert ids:' + str(result.inserted_ids)

print '\n ====iterating ===='
#for post in posts.find():
#    print 'iter post:' + str(post)

print '\n finding Mike:'
for post in posts.find({'author': 'Mike'}):
    print 'find Mike: ' + str(post)


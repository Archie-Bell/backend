import pymongo
import os

cluster = pymongo.MongoClient(os.getenv('MONGO_DB_URI'))
db = cluster[os.getenv('MONGO_DB_NAME')]
_collection = os.getenv('MISSING_PERSONS_COLLECTION')
collection = db[_collection]
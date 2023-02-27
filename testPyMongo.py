import pymongo
import numpy as np

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
testplatformDB = myclient["TestplatformDatabase"]

userCollection = testplatformDB['Users']

cursor = userCollection.find({})
for document in cursor:
    print(document['_id'])

    
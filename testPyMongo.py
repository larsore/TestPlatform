import pymongo
import numpy as np

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
testplatformDB = myclient["FIDOServer"]

userCollection = testplatformDB['Users']

#userCollection.delete_many({})

cursor = userCollection.find({})
for document in cursor:
    print(document)


"""cursor = userCollection.find({})
for document in cursor:
    print(document)"""
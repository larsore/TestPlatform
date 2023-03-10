import pymongo
import numpy as np

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
testplatformDB = myclient["FIDOServer"]

userCollection = testplatformDB['Users']

#cursor = userCollection.delete_many({})


    
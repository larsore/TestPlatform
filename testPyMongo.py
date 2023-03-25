import pymongo
import numpy as np

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
testplatformDB = myclient["FIDOServer"]

authenticatorCollection = testplatformDB['Authenticators']
"""
docs = authenticatorCollection.find({})

for doc in docs:
    print(doc)
"""
authenticatorCollection.delete_many({})


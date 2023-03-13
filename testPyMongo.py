import pymongo
import numpy as np

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
testplatformDB = myclient["FIDOServer"]

userCollection = testplatformDB['Users']

#cursor = userCollection.delete_many({})

col_list = testplatformDB.list_collection_names()
print ("collections on the unwanted db:", col_list)
myclient.drop_database('Users')



    
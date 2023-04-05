import pymongo

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
testplatformDB = myclient["FIDOServer"]

collection = testplatformDB['Authenticators']

username = "lars"





collection.delete_many({})


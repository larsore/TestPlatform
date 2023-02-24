import pymongo
import numpy as np

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
testplatformDB = myclient["TestplatformDatabase"]

userCollection = testplatformDB['Users']

myDict = {
    'seed': 12,
    '_id': np.asarray([[1, 2, 3], [4, 5, 6], [7, 8, 9]]).tobytes()
}

t = np.asarray([[1, 2, 3], [4, 5, 6], [7, 8, 9]])

print(userCollection.find_one({'_id': t.tobytes()}))
    
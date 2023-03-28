import pymongo
import os
import uuid

class Handler:
    
    credentials = {}

    RPName = "NTNU Master"
    RPID = "6c18e796-49d4-43a5-9371-6c9ea17c6222" # Just a random UUID for this RP

    def __init__(self):
        dbClient = pymongo.MongoClient(('mongodb://localhost:27017/'))
        db = dbClient['FIDOServer']
        userCollection = db['Users']

    @staticmethod
    def getChallenge():
        return os.urandom(64).hex()
    

    @staticmethod
    def getPublicKeyParams():
        return {
            "alg": "BabyDilithium",
            "n": 1280,
            "m": 1690,
            "q": 8380417,
            "eta": 5,
            "gamma": 523776
        }


    @classmethod
    def handleRegister(cls, body):
        credential = {}

        challenge = Handler.getChallenge()
        pubKeyParams = Handler.getPublicKeyParams()

        userID = str(uuid.uuid4())

        publicKey = {
            "attestaion": "none",
            "authenticatorSelection": {
                "authenticatorAttachment": "platform",
                "requireResidentKey": "true",
                "userVerification": "required"
            },
            "challenge": challenge,
            "excludeCredentials": [],
            "pubKeyCredParams": [pubKeyParams],
            "rp": {
                "id": cls.RPID,
                "name": cls.RPName
            },
            "timeout": 30, #sekunder
            "user": {
                "displayname": body["username"],
                "id": userID
            }
        }

        





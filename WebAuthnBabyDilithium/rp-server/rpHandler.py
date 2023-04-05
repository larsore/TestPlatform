import pymongo
import os
import time
import json
from hashlib import sha256

class Handler:
    
    credentials = {}

    RPName = "NTNU Master"
    RPID = None

    credentialCollection = None

    @classmethod
    def __init__(cls, RPID):
        cls.RPID = RPID

        dbClient = pymongo.MongoClient(('mongodb://localhost:27017/'))
        db = dbClient['FIDOServer']
        cls.credentialCollection = db['Credentials']

    @staticmethod
    def getChallenge():
        return os.urandom(64).hex()
    

    @staticmethod
    def getPublicKeyParams():
        return {
            "algName": "BabyDilithium",
            "n": 1280,
            "m": 1690,
            "q": 8380417,
            "eta": 5,
            "gamma": 523776
        }
    
    @classmethod
    def getRPID(cls):
        return cls.RPID

    @classmethod
    def handleRegister(cls, body):
        print(body)

        if cls.credentialCollection != None:
            cursor = cls.credentialCollection.find({"username": body["username"]})
            if len(list(cursor)) > 0:
                return json.dumps("Username taken!")

        challenge = Handler.getChallenge()
        pubKeyParams = Handler.getPublicKeyParams()
        timeout = 10 #sekunder

        response = {
            "challenge": challenge,
            "pubKeyCredParams": pubKeyParams,
            "rp": {
                "id": cls.RPID,
                "name": cls.RPName
            },
            "timeout": timeout, 
            "username": body["username"]
        }

        cls.credentials[body["authenticator_id"]] = {
            "username": body["username"],            
            "challenge": challenge
        }

        #TODO: Timer hos RP!!

        return json.dumps(response)
    
    @classmethod
    def handleRegisterResponse(cls, body):
        print(body.keys())

        h = sha256()
        h.update(cls.RPID)
        h.update(cls.credentials[body["authenticator_id"]]["challenge"])

        if h.hexdigest() == body["client_data"] and Handler.verifySig(pubKey=body["public_key"], sig=body["signature"]):
            docs = cls.credentialCollection.find({"username": cls.credentials[body["authenticator_id"]]["username"]})
            if len(list(docs)) == 0:
                doc = {
                    "username":cls.credentials[body["authenticator_id"]]["username"],
                    "authenticator_id":body["authenticator_id"],
                    "credential_id":body["credential_id"],
                    "pubKey":body["public_key"]
                }
                cursor = cls.credentialCollection.insert_one(doc)
                print(cursor.inserted_id+" added to credential collection")
                cls.credentials.pop(body["authenticator_id"], None)
                return json.dumps("Success")
            return json.dumps("User already registered")
        return json.dumps("Clientdata or signature failed!")
  

    @staticmethod
    def verifySig(pubKey, sig):
        seed = pubKey["seed"]
        t = pubKey["t"]
        w = sig["w"]
        z1 = sig["z1"]
        z2 = sig["z2"]
        c = sig["c"]
        #TODO: Fullfør signature





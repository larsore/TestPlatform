import pymongo
import os
import numpy as np
import json
from hashlib import sha256, shake_128
from threading import Timer


class Handler:

    n = 1280
    m = 1690
    q = 8380417
    eta = 5
    gamma = 523776

    SHAKElength = 13
    
    credentials = {}
    isActive = {}

    RPName = "NTNU Master"
    RPID = None

    timeout = 30 #sekunder
    timers = {}

    dbClient = pymongo.MongoClient(('mongodb://localhost:27017/'))
    db = dbClient['FIDOServer']
    credentialCollection = db['Credentials']

    @classmethod
    def __init__(cls, RPID):
        cls.RPID = RPID
        docs = cls.credentialCollection.find()
        for doc in docs:
            cls.credentials[doc["username"]] = {    
                "authenticator_id": doc["authenticator_id"],
                "A": {
                    "credential_id": doc["credential_id"],
                    "pubKey": doc["pubKey"]
                },
                "completed": False,
                "timedOut": False
            }
            cls.isActive[doc["username"]] = {
                "R": False,
                "A": False
            }
        for key in list(cls.credentials.keys()):
            print(key, cls.credentials[key]["authenticator_id"])

    @staticmethod
    def getChallenge():
        return os.urandom(64).hex()
    

    @classmethod
    def getPublicKeyParams(cls):
        return {
            "algName": "BabyDilithium",
            "n": cls.n,
            "m": cls.m,
            "q": cls.q,
            "eta": cls.eta,
            "gamma": cls.gamma
        }
    
    @classmethod
    def getRPID(cls):
        return cls.RPID
    
    @classmethod
    def handleLogin(cls, body):
        if body["username"] not in list(cls.credentials):
            return json.dumps("User with username: '"+body["username"]+"' has not registered...")
    
        challenge = Handler.getChallenge()
        cls.credentials[body["username"]]["challenge"] = challenge

        credID = cls.credentials[body["username"]]["A"]["credential_id"]
        authID = cls.credentials[body["username"]]["authenticator_id"]

        if body["username"] in list(cls.isActive.keys()) and cls.isActive[body["username"]]["A"]:
            return json.dumps(body["username"]+" is in the middle of an authentication procedure...")

        cls.timers[body["username"]] = Timer(cls.timeout, cls.handleTimeout, args=(body["username"], False ,))
        cls.timers[body["username"]].start()
        cls.credentials[body["username"]]["timedOut"] = False
        print("Timer started!!")
        cls.isActive[body["username"]]["A"] = True
        return json.dumps({
            "rp_id":cls.RPID,
            "challenge":challenge,
            "credential_id":credID,
            "timeout":cls.timeout,
            "authenticator_id":authID
        })
    
    @classmethod
    def handleLoginResponse(cls, body):
        cls.isActive[body["username"]]["A"] = False
        h1 = sha256()
        h1.update(cls.RPID.encode())
        h1.update(cls.credentials[body["username"]]["challenge"].encode())

        h2 = sha256()
        h2.update(body["rp_id"].encode())
        h2.update(body["challenge"].encode())

        pubKey = cls.credentials[body["username"]]["A"]["pubKey"]
        pubKey["t"] = np.frombuffer(pubKey["t"], dtype=int)

        signature = {
            "w": np.array(json.loads(body["w"]), dtype=int),
            "c": int(body["c"]),
            "z1": np.array(json.loads(body["z1"]), dtype=int),
            "z2": np.array(json.loads(body["z2"]), dtype=int)
        }

        if h1.hexdigest() == h2.hexdigest() and sha256(cls.RPID.encode()).hexdigest() == body["authenticator_data"] and Handler.verifySig(pubKey=pubKey, sig=signature, clientData=h1.hexdigest()):
            if not cls.credentials[body["username"]]["timedOut"]:
                cls.timers[body["username"]].cancel()

                cls.credentials[body["username"]]["completed"] = True    
                return json.dumps("Successfully logged in as "+body["username"])
            cls.credentials[body["username"]]["timedOut"] = False
            return json.dumps({
                "msg": "Timed out bitch!", 
                "reason": "timeout"})
        cls.isActive[body["username"]]["A"] = False
        return json.dumps({
            "msg": "ClientDataJSON, authData or signature failed!", 
            "reason": "cryptoVerificationFailure"})
        

    @classmethod
    def handleRegister(cls, body):
        if body["username"] in list(cls.credentials.keys()):
            return json.dumps(body["username"]+" already registered")

        challenge = Handler.getChallenge()
        pubKeyParams = cls.getPublicKeyParams()

        response = {
            "challenge": challenge,
            "pubKeyCredParams": pubKeyParams,
            "rp": {
                "id": cls.RPID,
                "name": cls.RPName
            },
            "timeout": cls.timeout
        }

        cls.credentials[body["username"]] = {
            "authenticator_id": body["authenticator_id"], 
            "challenge": challenge,
            "A": {
                "credential_id": "",
                "pubKey": {}
            },
            "completed": False,
            "timedOut": False
        }

        cls.isActive[body["username"]] = {
            "R": True,
            "A": False
        }

        cls.timers[body["username"]] = Timer(cls.timeout, cls.handleTimeout, args=(body["username"], True ,))
        cls.timers[body["username"]].start()
        print("Timer started!!")

        return json.dumps(response)


    @classmethod
    def handleTimeout(cls, username, isReg):
        print("TIMEOUT")
        if username not in list(cls.credentials.keys()):
            return
        if cls.credentials[username]["completed"]:
            if isReg:
                cls.isActive[username]["R"] = False
                return
            else:
                cls.isActive[username]["A"] = False
                return
        cls.credentials[username]["timedOut"] = True


    @classmethod
    def handleRegisterResponse(cls, body):
        cls.isActive[body["username"]]["R"] = False
        h = sha256()
        h.update(cls.RPID.encode())
        h.update(cls.credentials[body["username"]]["challenge"].encode())

        pubKey = {
            "t": np.array(json.loads(body["public_key_t"]), dtype=int),
            "seed": int(body["public_key_seed"])
        }
        signature = {
            "w": np.array(json.loads(body["w"]), dtype=int),
            "c": int(body["c"]),
            "z1": np.array(json.loads(body["z1"]), dtype=int),
            "z2": np.array(json.loads(body["z2"]), dtype=int)
        }

        if h.hexdigest() == body["client_data"] and Handler.verifySig(pubKey=pubKey, sig=signature, clientData=h.hexdigest()):
            if not cls.credentials[body["username"]]["timedOut"]:
                cls.timers[body["username"]].cancel()
                docs = cls.credentialCollection.find({"username": body["username"]})
                if len(list(docs)) == 0:
                    doc = {
                        "username":body["username"],
                        "authenticator_id":body["authenticator_id"],
                        "credential_id":body["credential_id"],
                        "pubKey":{
                            "t": pubKey["t"].tobytes(),
                            "seed": pubKey["seed"]
                        }
                    }
                    cursor = cls.credentialCollection.insert_one(doc)
                    print(str(cursor.inserted_id)+" added to credential collection")
                    cls.credentials[body["username"]]["completed"] = True
                    cls.credentials[body["username"]]["A"]["credential_id"] = body["credential_id"]
                    cls.credentials[body["username"]]["A"]["pubKey"] = pubKey
                    return json.dumps(body["username"]+" is now registered!")
                cls.credentials.pop(body["username"], None)
                return json.dumps({
                    "msg": "User already registered for some reason", 
                    "reason": "userAlreadyRegistered"
                    })
            cls.credentials.pop(body["username"], None)
            return json.dumps({
                "msg": "Timed out bitch!", 
                "reason": "timeout"})
        cls.credentials.pop(body["username"], None)
        return json.dumps({
            "msg": "Clientdata or signature failed!", 
            "reason": "cryptoVerificationFailure"})
  
    @classmethod
    def handleRegisterFailed(cls, body):
        cls.isActive[body["username"]]["R"] = False
        result = cls.credentials.pop(body["username"], None)
        if result != None:
            return json.dumps("We have registered that "+body["username"]+" failed registration")
        return json.dumps(body["username"]+" never tried to register...")
    
    @classmethod
    def handleLoginFailed(cls, body):
        cls.isActive[body["username"]]["A"] = False
        return json.dumps("We have registered that "+body["username"]+" failed authentication")
    
    @classmethod
    def computeSignatureChallenge(cls, A, t, w, clientData):
        shake = shake_128()
        shake.update(A.tobytes())
        shake.update(t.tobytes())
        shake.update(w.tobytes())
        shake.update(clientData.encode())
        shakeInt = int(shake.hexdigest(2), 16)
        if len(str(bin(shakeInt)))<=cls.SHAKElength+2:
            computedC = int(bin(shakeInt)[2:], 2) - 2**(cls.SHAKElength-1)
        else:
            computedC = int(bin(shakeInt)[-cls.SHAKElength:], 2) - 2**(cls.SHAKElength-1)
        
        return computedC


    @classmethod
    def verifySig(cls, pubKey, sig, clientData):
        seed = pubKey["seed"]
        np.random.seed(seed)

        startA = []
        for i in range(cls.n):
            startA.append(np.random.randint(0, cls.q, cls.m))
        A = np.array(startA)

        t = pubKey["t"]
        w = sig["w"]
        z1 = sig["z1"]
        z2 = sig["z2"]
        c = sig["c"]
        
        computedC = cls.computeSignatureChallenge(A, t, w, clientData)

        if computedC != c:
            print("Not the same challenge")
            return False
        # Check length
        if (not np.all(np.isin(z1, np.arange(-(cls.gamma-cls.eta), (cls.gamma-cls.eta)+1)))) or (not np.all(np.isin(z2, np.arange(-(cls.gamma-cls.eta), (cls.gamma-cls.eta)+1)))):
            print("z1 or z2 is not short...")
            return False
        if not np.array_equal((np.inner(A, z1) + z2 - c*t)%cls.q, w):
            print("Signature is not equal...")
            return False
        return True
    


        





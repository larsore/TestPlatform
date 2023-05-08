import pymongo
import os
import numpy as np
from numpy.polynomial import Polynomial
import json
from hashlib import sha256, shake_256
from threading import Timer


class Handler:

    q = None
    beta = None
    d = None
    n = None
    m = None
    gamma = None 
    approxBeta = None 
    hashSize = None
    f = None 
    ballSize = None 
    
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
        
    @classmethod
    def setParameters(cls, q, beta, d, n, m, gamma, hashSize, ballSize):
        cls.q = q
        cls.beta = beta
        cls.d = d
        cls.n = n
        cls.m = m
        cls.gamma = gamma
        cls.hashSize = hashSize
        cls.ballSize = ballSize
        cls.approxBeta = int((q-1)/16)
        fCoeff = np.array([1]+[0]*(d-2)+[1])
        cls.f = np.polynomial.Polynomial(fCoeff)


    @staticmethod
    def getChallenge():
        return os.urandom(64).hex()
    

    @classmethod
    def getPublicKeyParams(cls):
        return {
            "algName": "BabyDilithium",
            "q": cls.q,
            "beta": cls.beta,
            "d": cls.d,
            "n": cls.n,
            "m": cls.m,
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
        pubKeyVerify = {
            "t": Handler.coeffsToPolynomial(np.array(pubKey["t"])),
            "seedVector": np.array(pubKey["seedVector"], dtype=int)
        }
        
        signature = {
            "w": Handler.coeffsToPolynomial(np.array(json.loads(body["w"]), dtype=int)),
            "c": str(body["c"]),
            "z1": Handler.coeffsToPolynomial(np.array(json.loads(body["z1"]), dtype=int)),
            "z2": Handler.coeffsToPolynomial(np.array(json.loads(body["z2"]), dtype=int))
        }

        if h1.hexdigest() == h2.hexdigest() and sha256(cls.RPID.encode()).hexdigest() == body["authenticator_data"] and Handler.verifySig(pubKey=pubKeyVerify, sig=signature, clientData=h1.hexdigest()):
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

    @staticmethod
    def coeffsToPolynomial(coeffs):
        if coeffs.size>1:
            poly = []
            for c in coeffs:
                poly.append(Polynomial(c))
            return np.array(poly)
        return Polynomial(coeffs)
    
    @staticmethod
    def polynomialToCoeffs(poly):
        coeffs = []
        for p in poly:
            coeffs.append(list(p.coef))
        return coeffs
       
    @classmethod
    def handleRegisterResponse(cls, body):
        cls.isActive[body["username"]]["R"] = False
        h = sha256()
        h.update(cls.RPID.encode())
        h.update(cls.credentials[body["username"]]["challenge"].encode())
    
        pubKey = {
            "t": Handler.coeffsToPolynomial(np.array(json.loads(body["public_key_t"]), dtype=int)),
            "seedVector": np.array(json.loads(body["public_key_seed"]), dtype=int)
        }
        signature = {
            "w": Handler.coeffsToPolynomial(np.array(json.loads(body["w"]), dtype=int)),
            "c": str(body["c"]),
            "z1": Handler.coeffsToPolynomial(np.array(json.loads(body["z1"]), dtype=int)),
            "z2": Handler.coeffsToPolynomial(np.array(json.loads(body["z2"]), dtype=int))
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
                            "t": Handler.polynomialToCoeffs(pubKey["t"]),
                            "seedVector": pubKey["seedVector"].tolist()
                        }
                    }
                    cursor = cls.credentialCollection.insert_one(doc)
                    print(str(cursor.inserted_id)+" added to credential collection")
                    cls.credentials[body["username"]]["completed"] = True
                    cls.credentials[body["username"]]["A"]["credential_id"] = body["credential_id"]

                    dictPubKey = {
                        "t": np.array(json.loads(body["public_key_t"]), dtype=int),
                        "seedVector": pubKey["seedVector"].tolist()
                    }

                    cls.credentials[body["username"]]["A"]["pubKey"] = dictPubKey
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
    def hashToBall(cls, shake):
        cCoeffs = np.zeros(256, dtype=int)
        s = ""
        h = shake.digest(cls.hashSize)
        k = 0
        while True:
            s+=(bin(h[k])[2:])
            k+=1
            if len(s) >= cls.ballSize:
                break

        taken = []
        start = 196
        for i in range(start, 256):
            j = 257
            while j > i:
                if h[k] not in taken:
                    j = h[k]
                k+=1
            taken.append(j)
            cCoeffs[i] = cCoeffs[j]
            cCoeffs[j] = (-1)**int(s[i-start])
        
        return cCoeffs

    @classmethod
    def verifySig(cls, pubKey, sig, clientData):
        seedVector = pubKey["seedVector"]
        rng = np.random.default_rng(seedVector)

        startA = []
        ACoeffs = []
        for _ in range(cls.n):
            startA.append(np.array([Polynomial(rng.integers(0, cls.q, cls.d)) for _ in range(cls.m)]))
            for i in range(cls.m):
                ACoeffs.append(startA[-1][i].coef)
        A = np.array(startA)

        t = pubKey["t"]
        w = sig["w"]
        z1 = sig["z1"]
        z2 = sig["z2"]
        c = sig["c"]

        h = shake_256()
        h.update(np.array(ACoeffs).tobytes())
        h.update(np.array(Handler.polynomialToCoeffs(t)).tobytes())
        h.update(np.array(Handler.polynomialToCoeffs(w)).tobytes())
        h.update(clientData.encode())

        if h.hexdigest(17) != c:
            print("Not the same challenge")
            return False
        
        cPoly = Polynomial(cls.hashToBall(h))
        
        ct = np.array([cPoly*p for p in t])
        
        r = np.inner(A, z1)+z2-ct
        r = np.array([Polynomial((p % cls.f).coef % cls.q) for p in r])
        if not np.array_equal(r, w):
            print("Signature is not equal...")
            return False
        
        max = cls.approxBeta
        min = -cls.approxBeta
        
        concatenatedList = np.array(Handler.polynomialToCoeffs(z1) + Handler.polynomialToCoeffs(z2)).flatten()
        
        for coeff in concatenatedList:
            if coeff > max:
                max = coeff
            elif coeff < min:
                min = coeff

        if max > cls.approxBeta or min < -cls.approxBeta:
            print("z1 or z2 not short...")
            return False

        return True
    


        





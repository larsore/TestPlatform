import pymongo
import os
import numpy as np
from numpy.polynomial import Polynomial
import json
from hashlib import sha256, shake_256, shake_128
from threading import Timer

class Handler:

    q = None
    beta = None
    d = None
    n = None
    m = None
    gamma = None 
    approxBeta = None 
    f = None 
    eta = None 
    
    credentials = {}
    isActive = {}
    timers = {}
    timeout = 30 #sekunder

    RPName = "NTNU Master"
    RPID = None

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
        print('-----'+'REGISTERED USERS'+'-----')
        print('--'+'username'+'--'+'authenticator ID'+'--')
        for key in list(cls.credentials.keys()):
            print(key, cls.credentials[key]["authenticator_id"])
        
    @classmethod
    def setParameters(cls, q, beta, d, n, m, gamma, eta):
        cls.q = q
        cls.beta = beta
        cls.d = d
        cls.n = n
        cls.m = m
        cls.gamma = gamma
        cls.eta = eta
        cls.approxBeta = int((q-1)/16)
        fCoeff = np.array([1]+[0]*(d-2)+[1])
        cls.f = np.polynomial.Polynomial(fCoeff)

    @staticmethod
    def getChallenge():
        return os.urandom(64).hex()
    
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
        print("Timer for %s has started" %(body["username"]))
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
            "Aseed": pubKey["Aseed"]
        }
        signature = {
            "omega": str(body["omega"]),
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
                "msg": "Timed out!", 
                "reason": "timeout"})
        cls.isActive[body["username"]]["A"] = False
        return json.dumps({
            "msg": "clientDataJSON, authData or signature failed!", 
            "reason": "cryptoVerificationFailure"})
        
    @classmethod
    def handleRegister(cls, body):
        if body["username"] in list(cls.credentials.keys()):
            return json.dumps(body["username"]+" already registered")
        
        for key in list(cls.credentials.keys()):
            if body["authenticator_id"] == cls.credentials[key]["authenticator_id"]:
                return json.dumps("Authenticator is already registered to another user.")
        
        challenge = Handler.getChallenge()
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
        print("Timer for %s has started" %(body["username"]))

        return json.dumps({
            "challenge": challenge,
            "rp": {
                "id": cls.RPID,
                "name": cls.RPName
            },
            "timeout": cls.timeout
        })

    @classmethod
    def handleTimeout(cls, username, isReg):
        print("TIMEOUT for", username)
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
        if cls.credentials[body["username"]]["timedOut"]:
            cls.credentials.pop(body["username"], None)
            return json.dumps({
                "msg": "Timed out!", 
                "reason": "timeout"})

        cls.isActive[body["username"]]["R"] = False
        h = sha256()
        h.update(cls.RPID.encode())
        h.update(cls.credentials[body["username"]]["challenge"].encode())

        if h.hexdigest() == body["client_data"]:
            cls.timers[body["username"]].cancel()
            docs = cls.credentialCollection.find({"username": body["username"]})
            if len(list(docs)) == 0:
                doc = {
                    "username":body["username"],
                    "authenticator_id":body["authenticator_id"],
                    "credential_id":body["credential_id"],
                    "pubKey":{
                        "t": json.loads(body["public_key_t"]),
                        "Aseed": str(body["public_key_seed"])
                    }
                }
                cursor = cls.credentialCollection.insert_one(doc)
                print(str(cursor.inserted_id)+" added to credential collection")
                cls.credentials[body["username"]]["completed"] = True
                cls.credentials[body["username"]]["A"]["credential_id"] = body["credential_id"]
                dictPubKey = {
                    "t": np.array(json.loads(body["public_key_t"]), dtype=int),
                    "Aseed": str(body["public_key_seed"])
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
            "msg": "Not the same clientData!", 
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
    def hashToBall(cls, seed):
        cCoeffs = np.zeros(256, dtype=int)
        s = ""
        k = 0
        shake = shake_256(seed)
        while True:
            s+=(bin(shake.digest(k+1)[k])[2:])
            k+=1
            if len(s) >= cls.eta:
                break

        taken = []
        start = 256-cls.eta
        for i in range(start, 256):
            j = 257
            while j > i:
                candidate = shake.digest(k+1)[k]
                if candidate not in taken:
                    j = candidate
                k+=1
            taken.append(j)
            cCoeffs[i] = cCoeffs[j]
            cCoeffs[j] = (-1)**int(s[i-start])
        return cCoeffs

    @classmethod
    def expandA(cls, seed):
        h = shake_128(seed)
        A = []
        repr = 0
        for _ in range(cls.n):
            row = []
            for _ in range(cls.m):
                coefs = []
                while len(coefs) < cls.d:
                    h.update(str(repr).encode())
                    sample = h.digest(3)
                    b0 = int(bin(sample[0]), 2)
                    b1 = int(bin(sample[1]), 2)
                    b2mark = int('0'+bin(sample[2])[2:].rjust(8, '0')[1:], 2)
                    candid = b2mark*2**(16)+b1*2**(8)+b0
                    if candid < cls.q:
                        coefs.append(candid)
                    repr+=1
                row.append(Polynomial(coefs))
            A.append(row)
        return np.array(A)

    @classmethod
    def verifySig(cls, pubKey, sig, clientData):
        
        A = cls.expandA(pubKey["Aseed"].encode())

        t = pubKey["t"]
        omega = sig["omega"]
        z1 = sig["z1"]
        z2 = sig["z2"]
        c = sig["c"]

        h = shake_256()
        h.update(pubKey["Aseed"].encode())
        h.update(np.array(Handler.polynomialToCoeffs(t)).tobytes())
        h.update(omega.encode())
        h.update(clientData.encode())

        if h.hexdigest(48) != c:
            print("Not the same challenge")
            return False
        
        cPoly = Polynomial(cls.hashToBall(h.hexdigest(48).encode()))
        ct = np.array([cPoly*p for p in t])
        r = np.inner(A, z1)+z2-ct
        r = np.array([Polynomial((p % cls.f).coef % cls.q) for p in r])

        if not shake_256(np.array(Handler.polynomialToCoeffs(r), dtype=int).tobytes()).hexdigest(48) == omega:
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
    


        





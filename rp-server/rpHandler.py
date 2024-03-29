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
        if body["username"] in list(cls.isActive.keys()) and cls.isActive[body["username"]]["A"]:
            return json.dumps(body["username"]+" is in the middle of an authentication procedure...")
        challenge = Handler.getChallenge()
        cls.credentials[body["username"]]["challenge"] = challenge
        credID = cls.credentials[body["username"]]["A"]["credential_id"]
        authID = cls.credentials[body["username"]]["authenticator_id"]
        cls.timers[body["username"]] = Timer(cls.timeout, cls.handleTimeout, args=(body["username"], False ,))
        cls.timers[body["username"]].start()
        cls.credentials[body["username"]]["timedOut"] = False
        cls.isActive[body["username"]]["A"] = True
        return json.dumps({
            "rp_id":cls.RPID,
            "challenge":challenge,
            "credential_id":credID,
            "timeout":cls.timeout,
            "authenticator_id":authID,
            "random_int": str(np.random.randint(low=1, high=100000))
        })
    
    @classmethod
    def handleLoginResponse(cls, body):
        if cls.credentials[body["username"]]["timedOut"]:
            cls.credentials[body["username"]]["timedOut"] = False
            return json.dumps({
                "msg": "Timed out!", 
                "reason": "timeout"})
        cls.isActive[body["username"]]["A"] = False
        expectedHash = sha256()
        expectedHash.update(cls.RPID.encode())
        expectedHash.update(cls.credentials[body["username"]]["challenge"].encode())
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
        if expectedHash.hexdigest() == body["client_data"] and sha256(cls.RPID.encode()).hexdigest() == body["authenticator_data"] and Handler.verifySig(pubKey=pubKeyVerify, sig=signature, clientData=expectedHash.hexdigest()):
            cls.timers[body["username"]].cancel()
            return json.dumps("Successfully logged in as "+body["username"])
        return json.dumps({
            "msg": "clientDataJSON, authData or signature failed!", 
            "reason": "cryptoVerificationFailure"})
        
    @classmethod
    def handleRegister(cls, body):
        if body["username"] in list(cls.credentials.keys()):
            return json.dumps(body["username"]+" already registered")
        challenge = Handler.getChallenge()
        cls.credentials[body["username"]] = {
            "challenge": challenge,
            "A": {
                "credential_id": "",
                "pubKey": {}
            },
            "timedOut": False
        }
        cls.isActive[body["username"]] = {
            "R": True,
            "A": False
        }
        cls.timers[body["username"]] = Timer(cls.timeout, cls.handleTimeout, args=(body["username"], True ,))
        cls.timers[body["username"]].start()
        return json.dumps({
            "challenge": challenge,
            "rp_id": cls.RPID,
            "timeout": cls.timeout
        })

    @classmethod
    def handleTimeout(cls, username, isReg):
        print("TIMEOUT for", username)
        if username not in list(cls.credentials.keys()):
            return
        cls.credentials[username]["timedOut"] = True
        if isReg:
            cls.isActive[username]["R"] = False
            return
        else:
            cls.isActive[username]["A"] = False
            return

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
        expectedHash = sha256()
        expectedHash.update(cls.RPID.encode())
        expectedHash.update(cls.credentials[body["username"]]["challenge"].encode())
        if expectedHash.hexdigest() == body["client_data"]:
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
                cls.credentialCollection.insert_one(doc)
                cls.credentials[body["username"]]["A"]["credential_id"] = body["credential_id"]
                dictPubKey = {
                    "t": np.array(json.loads(body["public_key_t"]), dtype=int),
                    "Aseed": str(body["public_key_seed"])
                }
                cls.credentials[body["username"]]["A"]["pubKey"] = dictPubKey
                cls.credentials[body["username"]]["authenticator_id"] = body["authenticator_id"]
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
        start = cls.d-cls.eta
        for i in range(start, cls.d):
            j = cls.d+1
            while j > i:
                candidate = shake.digest(k+1)[k]
                if candidate not in taken:
                    j = candidate
                k+=1
            taken.append(j)
            cCoeffs[i] = cCoeffs[j]
            cCoeffs[j] = (-1)**int(s[i-start])
        return Polynomial(cCoeffs)

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
                    b2prime = int('0'+bin(sample[2])[2:].rjust(8, '0')[1:], 2)
                    candid = b2prime*2**(16)+b1*2**(8)+b0
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
        ACoeffs = []
        for row in A:
            r = []
            for poly in row:
                r.append(poly.coef)
            ACoeffs.append(r)
        expectedHash = shake_256()
        expectedHash.update(np.array(ACoeffs).tobytes())
        expectedHash.update(np.array(Handler.polynomialToCoeffs(t)).tobytes())
        expectedHash.update(omega.encode())
        expectedHash.update(clientData.encode())
        if expectedHash.hexdigest(48) != c:
            return False
        cPoly = cls.hashToBall(expectedHash.hexdigest(48).encode())
        ct = np.array([cPoly*p for p in t])
        omegaprime = np.inner(A, z1)+z2-ct
        omegaprime = np.array([Polynomial((p % cls.f).coef % cls.q) for p in omegaprime])
        if not shake_256(np.array(Handler.polynomialToCoeffs(omegaprime), dtype=int).tobytes()).hexdigest(48) == omega:
            return False
        concatenatedList = np.array(Handler.polynomialToCoeffs(z1) + Handler.polynomialToCoeffs(z2)).flatten()
        if np.any(np.absolute(concatenatedList) > cls.approxBeta):
            return False
        return True

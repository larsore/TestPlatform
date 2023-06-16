from collections import deque
import pymongo
import json
import time

class Handler:
    
    activeRequests = {}
    responseToClient = {}
    isActive = {}
    otpMapping = {}

    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    testplatformDB = myclient["FIDOServer"]
    authenticatorCollection = testplatformDB['Authenticators']

    @classmethod
    def __init__(cls):
        auths = cls.authenticatorCollection.find()
        for document in auths:
            cls.activeRequests[document["_id"]] = {
                "R": deque(),
                "A": deque(),
                "RPs": document["RPs"],
                "dismissed": False,
                "timedOut": False
            }
            cls.isActive[document["_id"]] = {
                "A": False,
                "R": False
            }
        print('-----'+'REGISTERED AUTHENTICATORS'+'-----')
        print('--'+'authenticator ID'+'--'+'RPs'+'--')
        for key in list(cls.activeRequests.keys()):
            rps = cls.activeRequests[key]["RPs"]
            for rp in rps:
                print(key, rp)
       
    @classmethod
    def handlePOSTClientRegister(cls, registerRequest):
        if registerRequest['otp'] not in list(cls.otpMapping.keys()):
            return json.dumps("OTP not valid")
        authID = cls.otpMapping[registerRequest['otp']]
        if authID in list(cls.activeRequests.keys()):
            if registerRequest["rp_id"] in cls.activeRequests[authID]["RPs"]:
                return json.dumps("Authenticator with specified ID has already registered with the given RP")
        if authID in list(cls.isActive.keys()) and cls.isActive[authID]["R"]:
                return json.dumps("Authenticator is currently registrating...")
        cls.activeRequests[authID] = {
            "R": deque(),
            "A": deque(),
            "RPs": [],
            "dismissed": False,
            "timedOut": False
        }
        if len(cls.activeRequests[authID]["R"]) == 0:
            cls.activeRequests[authID]["R"].append({
                "credential_id": "",
                "rp_id": registerRequest["rp_id"],
                "client_data": registerRequest["client_data"],
                "username": registerRequest["username"],
                "random_int": ""
            })
            cls.isActive[authID] = {
                "A": False,
                "R": True
            }
            timeout = int(registerRequest["timeout"])
            waitedTime = 0
            interval = 0.1
            while waitedTime <= timeout:
                waitedTime += interval
                time.sleep(interval)
                if cls.activeRequests[authID]["dismissed"]:
                    cls.activeRequests.pop(authID, None)
                    return json.dumps("Authenticator chose to dismiss the registration attempt")               
                if authID in list(cls.responseToClient.keys()):
                    response = cls.responseToClient.pop(authID, None)
                    cls.isActive[authID]["R"] = False
                    return json.dumps(response)
            cls.activeRequests.pop(authID, None)
            cls.isActive.pop(authID, None)
            return json.dumps("Timeout")
        return json.dumps("Pending registration already exists for the given authenticator")
        
    @classmethod
    def handlePOSTClientAuthenticate(cls, authenticateRequest):
        if authenticateRequest["authenticator_id"] in list(cls.isActive.keys()) and cls.isActive[authenticateRequest["authenticator_id"]]["A"]:
            return json.dumps("Authenticator is in the middle of an authentication procedure")
        if authenticateRequest["authenticator_id"] not in list(cls.activeRequests.keys()):
            return json.dumps("Authenticator with specified ID has not registered")
        if authenticateRequest["rp_id"] not in cls.activeRequests[authenticateRequest["authenticator_id"]]["RPs"]:
            return json.dumps("Authenticator with specified ID has not registered with the given RP")
        if len(cls.activeRequests[authenticateRequest["authenticator_id"]]["A"]) == 0:
            cls.activeRequests[authenticateRequest["authenticator_id"]]["A"].append({
                "credential_id": authenticateRequest["credential_id"],
                "rp_id": authenticateRequest["rp_id"],
                "client_data": authenticateRequest["client_data"],
                "username": authenticateRequest["username"],
                "random_int": authenticateRequest["random_int"]
            })
            cls.isActive[authenticateRequest["authenticator_id"]]["A"] = True
            cls.activeRequests[authenticateRequest["authenticator_id"]]["timedOut"] = False
            timeout = int(authenticateRequest["timeout"])
            waitedTime = 0
            interval = 0.1
            while waitedTime <= timeout:
                waitedTime += interval
                time.sleep(interval)
                if cls.activeRequests[authenticateRequest["authenticator_id"]]["dismissed"]:
                    cls.activeRequests[authenticateRequest["authenticator_id"]]["dismissed"] = False
                    return json.dumps("Authenticator chose to dismiss the authentication attempt")        
                if authenticateRequest["authenticator_id"] in list(cls.responseToClient.keys()):
                    response = cls.responseToClient.pop(authenticateRequest["authenticator_id"], None)
                    cls.isActive[authenticateRequest["authenticator_id"]]["A"] = False
                    return json.dumps(response)
            cls.activeRequests[authenticateRequest["authenticator_id"]]["A"] = deque()
            cls.activeRequests[authenticateRequest["authenticator_id"]]["timedOut"] = True
            cls.isActive[authenticateRequest["authenticator_id"]]["A"] = False
            return json.dumps("Timeout")
        return json.dumps("Pending authentication request already exists for the given authenticator")

    @classmethod
    def handleAuthenticatorUpdate(cls, body):
        cls.otpMapping.pop(body['old_otp'], None)
        cls.otpMapping[body['current_otp']] = body['authenticator_id']
        return json.dumps({"success": "OTP updated"})

    @classmethod
    def handlePOSTAuthenticator(cls, body):
        if body["authenticator_id"] not in list(cls.activeRequests.keys()):
            return json.dumps("Authenticator with specified ID has not been registered")
        activeRequests = cls.activeRequests[body["authenticator_id"]]
        if len(activeRequests["R"]) != 0:
            request = activeRequests["R"].pop()
            return json.dumps(request)
        elif len(activeRequests["A"]) != 0:
            request = activeRequests["A"].pop()
            return json.dumps(request)
        return json.dumps("No pending requests for authenticator")

    @classmethod
    def handleDismissal(cls, req):
        if req["action"] == "auth":
            if cls.activeRequests[req["authenticator_id"]]["timedOut"]:
                return json.dumps({"success": "Already timed out"})
            cls.isActive[req["authenticator_id"]]["A"] = False
            cls.activeRequests[req["authenticator_id"]]["dismissed"] = True
        else:
            if req["authenticator_id"] not in list(cls.activeRequests.keys()):
                return json.dumps({"success": "Already timed out"})
            cls.activeRequests[req["authenticator_id"]]["dismissed"] = True
            cls.isActive[req["authenticator_id"]]["R"] = False
        return json.dumps({"success": "Dismissed"})

    @classmethod
    def handlePOSTAuthenticatorRegister(cls, registerRequest):
        if registerRequest["authenticator_id"] not in list(cls.activeRequests.keys()):
            return json.dumps({"success": "Timed Out"})
        cls.activeRequests[registerRequest["authenticator_id"]]["RPs"].append(registerRequest["rp_id"])
        if registerRequest["authenticator_id"] not in list(cls.responseToClient.keys()):
            cls.responseToClient[registerRequest["authenticator_id"]] = {
                "credential_id": registerRequest["credential_id"],
                "public_key_t": registerRequest["public_key_t"],
                "public_key_seed": registerRequest["public_key_seed"],
                "client_data": registerRequest["client_data"],
                "authenticator_id": registerRequest["authenticator_id"]
            }
        docs = cls.authenticatorCollection.find({"_id": registerRequest["authenticator_id"]})
        if len(list(docs)) > 0:           
            cls.authenticatorCollection.update_one({"_id": registerRequest["authenticator_id"]}, {"$push": {"RPs", registerRequest["rp_id"]}})
        else:
            newDoc = {
                "_id": registerRequest["authenticator_id"],
                "RPs": [registerRequest["rp_id"]]  
            }
            cls.authenticatorCollection.insert_one(newDoc)
        return json.dumps({"success": "NS Auth Reg"})

    @classmethod
    def handlePOSTAuthenticatorAuthenticate(cls, authenticateRequest):
        if cls.activeRequests[authenticateRequest["authenticator_id"]]["timedOut"]:
            cls.activeRequests[authenticateRequest["authenticator_id"]]["timedOut"] = False
            return json.dumps({"success": "Timed Out"})
        if authenticateRequest["authenticator_id"] not in list(cls.responseToClient.keys()):
            cls.responseToClient[authenticateRequest["authenticator_id"]] = {
                "authenticator_data": authenticateRequest["authenticator_data"],
                "omega": authenticateRequest["omega"],
                "c": authenticateRequest["c"],
                "z1": authenticateRequest["z1"],
                "z2": authenticateRequest["z2"],
                "client_data": authenticateRequest["client_data"],
                "random_int": authenticateRequest["random_int"]
            }
        return json.dumps({"success": "NS Auth Auth"})
    
    @classmethod
    def handleClientRegisterFailed(cls, body):
        result = cls.activeRequests.pop(body["authenticator_id"], None)
        if result != None:
            cls.authenticatorCollection.delete_one({"_id": body["authenticator_id"]})
            return json.dumps("PollingServer have received that "+body["username"]+" was not registered at RP")
        return json.dumps("PollingServer have not received any registrationattempts for authID =  "+body["authenticator_id"]+"...")
    
    @classmethod
    def handleClientLoginFailed(cls, body):
        cls.activeRequests[body["authenticator_id"]]["A"] = deque()
        return json.dumps("PollingServer have recieved that "+body["username"]+" failed authentication...")
        
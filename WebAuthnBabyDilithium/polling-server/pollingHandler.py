from collections import deque
import pymongo
import json
import time

class Handler:
    
    activeRequests = {}

    responseToClient = {}

    dismissals = []
    timedOut = []

    handler = None

    first = True

    isAuthenticating = False

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
                "RPs": document["RPs"]
            }
        print(cls.activeRequests)

    @classmethod
    def updateDictOnFirstReq(cls, req):
        if cls.first:
            cursor = cls.authenticatorCollection.find({"_id": req["authenticator_id"]})
            for d in cursor:
                RPs = d["RPs"]
                cls.activeRequests[req["authenticator_id"]] = {
                    "R": deque(),
                    "A": deque(),
                    "RPs": RPs
                }
            cls.first = False
        
        
    @classmethod
    def handlePOSTClientRegister(cls, registerRequest):
        print(registerRequest)

        cls.updateDictOnFirstReq(registerRequest)

        if registerRequest["authenticator_id"] in list(cls.activeRequests.keys()):
            if registerRequest["rp_id"] in cls.activeRequests[registerRequest["authenticator_id"]]["RPs"]:
                return json.dumps("Authenticator with specified ID has already registered with the given RP")
        else:
            cls.activeRequests[registerRequest["authenticator_id"]] = {
                "R": deque(),
                "A": deque(),
                "RPs": []
            }

        stack = cls.activeRequests[registerRequest["authenticator_id"]]["R"] 

        if len(stack) == 0:
            stack.append({
                "credential_id": "",
                "rp_id": registerRequest["rp_id"],
                "client_data": registerRequest["client_data"],
                "username": registerRequest["username"]
            })

            timeout = int(registerRequest["timeout"])
            waitedTime = 0
            interval = 0.5
            while waitedTime <= timeout:
                waitedTime += interval
                time.sleep(interval)
                print("Waited for ", waitedTime, " seconds...")
                if registerRequest["authenticator_id"] in cls.dismissals:
                    cls.dismissals.remove(registerRequest["authenticator_id"])
                    cls.activeRequests[registerRequest["authenticator_id"]]["R"] = deque()
                    return json.dumps("Authenticator chose to dismiss the registration atttempt")
                
                if registerRequest["authenticator_id"] in list(cls.responseToClient.keys()):
                    response = cls.responseToClient.pop(registerRequest["authenticator_id"], None)
                    return json.dumps(response)
            cls.activeRequests[registerRequest["authenticator_id"]]["R"] = deque()
            cls.timedOut.append(registerRequest["authenticator_id"])
            return json.dumps("Timeout")
        
        return json.dumps("Pending registration already exists for the given authenticator")
    

    @classmethod
    def handlePOSTClientAuthenticate(cls, authenticateRequest):
        print(authenticateRequest)

        cls.updateDictOnFirstReq(authenticateRequest)

        if cls.isAuthenticating:
            return json.dumps("Authenticator is in the middle of an authentication procedure")
        
        if authenticateRequest["authenticator_id"] not in list(cls.activeRequests.keys()):
            return json.dumps("Authenticator with specified ID has not registered")

        if authenticateRequest["rp_id"] not in cls.activeRequests[authenticateRequest["authenticator_id"]]["RPs"]:
            return json.dumps("Authenticator with specified ID has not registered with the given RP")

        stack = cls.activeRequests[authenticateRequest["authenticator_id"]]["A"] 

        if len(stack) == 0:
            stack.append({
                "credential_id": authenticateRequest["credential_id"],
                "rp_id": authenticateRequest["rp_id"],
                "client_data": authenticateRequest["client_data"]
            })
            return json.dumps("Authenticate request added to polling server")
        
        return json.dumps("Pending authentication request already exists for the given authenticator")

    
    @classmethod
    def handleGETAuthenticator(cls, body):
        print(cls.activeRequests)
        if body["authenticator_id"] not in list(cls.activeRequests.keys()):
            return json.dumps("Authenticator with specified ID has not been registered")

        activeRequests = cls.activeRequests[body["authenticator_id"]]
        activeRegistrations = activeRequests["R"]
        activeAuthentications = activeRequests["A"]
        
        if len(activeRegistrations) != 0:
            request = activeRegistrations.pop()
            print(cls.activeRequests)
            return json.dumps({
                "credential_id": "",
                "rp_id": request["rp_id"],
                "client_data": request["client_data"],
                "username": request["username"]
            })
        
        elif len(activeAuthentications) != 0:
            request = activeAuthentications.pop()
            cls.isAuthenticating = True
            return json.dumps({
                "credential_id": request["credential_id"],
                "rp_id": request["rp_id"],
                "client_data": request["client_data"]
            })
             
        return json.dumps("No pending requests for authenticator")

    @classmethod
    def handleDismissal(cls, req, isAuth):
        print(req)
        if req["authenticator_id"] in cls.timedOut:
            cls.timedOut.remove(req["authenticator_id"])
            return json.dumps({"success": "Timed Out"})
        if isAuth:
            cls.isAuthenticating = False
        else:
            cls.dismissals.append(req["authenticator_id"])
        return json.dumps({"success": "NS Auth Reg"})

    @classmethod
    def handlePOSTAuthenticatorRegister(cls, registerRequest):
        print(registerRequest.keys())

        if registerRequest["authenticator_id"] in cls.timedOut:
            cls.timedOut.remove(registerRequest["authenticator_id"])
            return json.dumps({"success": "Timed Out"})

        cls.activeRequests[registerRequest["authenticator_id"]]["RPs"].append(registerRequest["rp_id"])

        if registerRequest["authenticator_id"] not in list(cls.responseToClient.keys()):
            cls.responseToClient[registerRequest["authenticator_id"]] = {
                "credential_id": registerRequest["credential_id"],
                "public_key": {
                    "t": registerRequest["public_key_t"],
                    "seed": registerRequest["public_key_seed"]
                },
                "client_data": registerRequest["client_data"],
                "authenticator_id": registerRequest["authenticator_id"],
                "signature": {
                    "w": registerRequest["w"],
                    "z1": registerRequest["z1"],
                    "z2": registerRequest["z2"],
                    "c": registerRequest["c"]
                }
            }

        docs = cls.authenticatorCollection.find({"_id": registerRequest["authenticator_id"]})

        if len(list(docs)) > 0:           
            cls.authenticatorCollection.update_one({"_id": registerRequest["authenticator_id"]}, {"$push": {"RPs", registerRequest["rp_id"]}})
        else:
            newDoc = {
                "_id": registerRequest["authenticator_id"],
                "RPs": [registerRequest["rp_id"]]  
            }
            cursor = cls.authenticatorCollection.insert_one(newDoc)
            print(cursor.inserted_id+" added to mongodb")

        return json.dumps({"success": "NS Auth Reg"})


    @classmethod
    def handlePOSTAuthenticatorAuthenticate(cls, authenticateRequest):
        print(authenticateRequest)
        
        cls.isAuthenticating = False

        return json.dumps({"success": "NS Auth Auth"})
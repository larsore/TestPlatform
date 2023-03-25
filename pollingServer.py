from collections import deque
import socket
import socketserver
import pymongo
import json

class PollingServer:
    
    activeRequests = {}

    handler = None

    first = True

    isAuthenticating = False

    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    testplatformDB = myclient["FIDOServer"]
    authenticatorCollection = testplatformDB['Authenticators']

    @classmethod
    def __init__(cls, handler):
        PollingServer.handler = handler
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
            print("dsad")
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
                return b"Authenticator with specified ID has already registered with the given RP"
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
                "client_data": registerRequest["client_data"]
            })
            return b"Registration request added to polling server"
        
        return b"Pending registration already exists for the given authenticator"
        


    @classmethod
    def handlePOSTClientAuthenticate(cls, authenticateRequest):
        print(authenticateRequest)

        cls.updateDictOnFirstReq(authenticateRequest)

        if cls.isAuthenticating:
            return b"Authenticator is in the middle of an authentication procedure"
        
        if authenticateRequest["authenticator_id"] not in list(cls.activeRequests.keys()):
            return b"Authenticator with specified ID has not registered"

        if authenticateRequest["rp_id"] not in cls.activeRequests[authenticateRequest["authenticator_id"]]["RPs"]:
            return b"Authenticator with specified ID has not registered with the given RP"

        stack = cls.activeRequests[authenticateRequest["authenticator_id"]]["A"] 

        

        if len(stack) == 0:
            stack.append({
                "credential_id": authenticateRequest["credential_id"],
                "rp_id": authenticateRequest["rp_id"],
                "client_data": authenticateRequest["client_data"]
            })
            return b"Authenticate request added to polling server"
        
        return b"Pending authentication request already exists for the given authenticator"

    
    @classmethod
    def handleGETAuthenticator(cls, authID):
        if authID not in list(cls.activeRequests.keys()):
            return b"Authenticator with specified ID has not been registered"

        activeRequests = cls.activeRequests[authID]
        activeRegistrations = activeRequests["R"]
        activeAuthentications = activeRequests["A"]
        
        if len(activeRegistrations) != 0:
            request = activeRegistrations.pop()
            print(cls.activeRequests)
            return json.dumps({
                "credential_id": "",
                "rp_id": request["rp_id"],
                "client_data": request["client_data"]
            }).encode()
        
        elif len(activeAuthentications) != 0:
            request = activeAuthentications.pop()
            cls.isAuthenticating = True
            return json.dumps({
                "credential_id": request["credential_id"],
                "rp_id": request["rp_id"],
                "client_data": request["client_data"]
            }).encode()
             
        return b"No pending requests for authenticator"

    @classmethod
    def handleDismissal(cls, req, isAuth):
        print(req)
        if isAuth:
            cls.isAuthenticating = False
        return json.dumps({"success": "NS Auth Reg"}).encode()

    @classmethod
    def handlePOSTAuthenticatorRegister(cls, registerRequest):
        print(registerRequest)

        cls.activeRequests[registerRequest["authenticator_id"]]["RPs"].append(registerRequest["rp_id"])

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

        return json.dumps({"success": "NS Auth Reg"}).encode()


    @classmethod
    def handlePOSTAuthenticatorAuthenticate(cls, authenticateRequest):
        print(authenticateRequest)
        
        cls.isAuthenticating = False

        return json.dumps({"success": "NS Auth Auth"}).encode()

if __name__ == "__main__":
    from handler import Handler
    pollingServer = PollingServer(Handler)
    PORT = 8000
    hostname = socket.gethostname()
    ip_address = "192.168.39.177"
    my_server = socketserver.TCPServer((ip_address, PORT), pollingServer.handler)
    print('Server started at ' + ip_address + ':' + str(PORT))
    my_server.serve_forever()
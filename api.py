import json
import http.server
import socketserver
from typing import Tuple
from http import HTTPStatus
import socket
import numpy as np
from routes import routes
import pymongo
from hashlib import sha256



class Handler(http.server.SimpleHTTPRequestHandler):
    challenge = 0 #128 bit, 16 byte
    rpID = 1 #TODO skal være en url?
    clientAddress = None

    #credentialDict = {}

    def __init__(self, request: bytes, client_address: Tuple[str, int], server: socketserver.BaseServer):
        super().__init__(request, client_address, server)
       
    #TODO lag truly random challenge
    def createChallenge(self):
        challenge = np.random.randint(0,1000)
        return challenge

    def startDatabase(self):
        dbClient = pymongo.MongoClient(('mongodb://localhost:27017/'))
        db = dbClient['FIDOServer']
        userCollection = db['Users']
        return userCollection
    
    @classmethod
    def setUsername(cls, username):
        cls.username = username

    @classmethod
    def getUsername(cls):
        return cls.username
    
    @classmethod
    def setChallenge(cls, challenge):
        cls.challenge = challenge

    @classmethod
    def getChallenge(cls):
        return cls.challenge
    
    @classmethod
    def setClientAddress(cls, clientAddress):
        cls.clientAddress = clientAddress
    
    @classmethod
    def getClientAddress(cls):
        return cls.clientAddress
    
    """
    def requiredKeysInRequest(self, requiredKeys, request):
        for key in requiredKeys:
            if key not in request:
                return False
            else:
                return True
    """

    def requiredKeysInRequest(self, requiredKeys, request):
        return all(key in request for key in requiredKeys)

    def verifySignature(self, c, A, t, w, m, z1, z2):
        h = sha256(A+t+w+m).hexdigest
        if c == h:
            if sha256((np.inner(A, z1) + z2 - c*t).tobytes()) == w:
                return True
        return False
    
   
    def do_GET(self):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        if self.path in routes:
            route_content = routes[self.path]
            return self.wfile.write(b'%s' % route_content.encode())
        else:
            return self.wfile.write(b'%s is not a valid path' % self.path.encode())

    def do_POST(self):       
        #Registrering
        if self.path == '/register':
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            registerRequest = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requiredKeys = ["username", "authenticator_nickname"]
            checkRequiredKeys = self.requiredKeysInRequest(requiredKeys,registerRequest)
            if not checkRequiredKeys:
                return self.wfile.write(b'Not all required fields present in request. The required fields are %s' % str(requiredKeys).encode())
            else:   
                userCollection = self.startDatabase() 
                requestReceivedFrom = self.client_address[0]

                self.setClientAddress(requestReceivedFrom) #Henter ip-adressen requesten ble sendt fra, setter denne globalt
                print("Set client address to:",requestReceivedFrom)

                if registerRequest == b'': #Hvis body er tom, return 400 bad request
                    return self.send_error(400, "Bad request")
                else:
                    self.send_response(HTTPStatus.OK)
                    #registerRequest = json.loads(self.data_string.decode('utf8').replace("'", '"'))
                    print("Recieved request from client:",registerRequest)
                
                    self.send_header("Content-type", "application/json") #TODO sende host her? sjekk hvilke headers som er mulige å sende
                    self.end_headers()

                    challenge = self.createChallenge() 
                    self.setChallenge(challenge=challenge)
                    self.expectedClientAddress = self.client_address[0] 
                    username = registerRequest.get("username") #avhengig av at kun én pers registrerer seg og verfifiserer seg om gangen. #TODO se på alternativ løsning
                    self.setUsername(username=username)

                    authenticatorNickname = registerRequest.get("authenticator_nickname")
                    checkUserExistence = userCollection.find_one({'_id': username})
                    
                    if checkUserExistence == None: #No instance of that username in database
                        doc = {
                            '_id': username,
                            'authenticator_nickname': authenticatorNickname
                        }
                        userCollection.insert_one(doc)

                        """
                        credentialUserId = int(sha256(json.dumps(doc).encode()).hexdigest(), 16)
                
                        print(credentialUserId)

                        self.credentialDict[credentialUserId] = username #Add new entry to dict: {username: credentialUserId}
                        print(self.credentialDict)
                        """

                        cred = {
                            "publicKey": {
                                "attestation": "none",
                                "authenticatorSelection": {
                                    "authenticatorAttachment": "platform",
                                    "requireResidentKey": True,
                                    "userVerification": "required"
                                },
                                "challenge": challenge, #TODO truly random challenge
                                "excludeCredentials": [],
                                "pubKeyCredParams": [
                                    {
                                        "alg": "baby-dilithium",
                                        "type": "public-key"
                                    }
                                ],
                                "rp": {
                                    "id": "masterthesis.com", #TODO må være samme som http origin
                                    "name": "Master Thesis"
                                },
                                "timeout": 30000, #30sek
                                "user": {
                                    "displayName": username,
                                    "id": username #Midlertidig for å linke username og credential sammen. 
                                }
                            }
                        }
                        print("hash:", sha256(str(self.rpID+self.getChallenge()).encode()).hexdigest())
                        return self.wfile.write(json.dumps(cred).encode()) #TODO sende host slik at client kan sjekke host==rpID
                    else:
                        self.send_error(409, "Username taken")
                        #TODO legg til sjekk på username + authenticator? Skal egentil være mulig å registrere seg flere ganger med samme brukernavn men med ny authenticator
                        return self.wfile.write(b"Brukernavn '%s' er allerede i bruk, prov med et nytt" % registerRequest.get("username").encode())
       
        elif self.path == "/register/verification": #siste sted i registreringsprosessen
            regAuthRequest = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requiredKeys = ["public_key", "credential_id", "client_data"]
            checkRequiredKeys = self.requiredKeysInRequest(requiredKeys,regAuthRequest)

            if not checkRequiredKeys:
                return self.wfile.write(b'Not all required fields present in request. The required fields are %s' % str(requiredKeys).encode())
            else:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-type", "application/json")
                self.end_headers()

                userCollection = self.startDatabase()

                challenge = self.getChallenge()
                expectedClientAddress = self.getClientAddress()

                verifyClientAddress = expectedClientAddress == self.client_address[0]
                verifyClientData = regAuthRequest.get("client_data") == sha256(str(self.rpID+challenge).encode()).hexdigest()
                verifyPublicKey = "public_key" in regAuthRequest

                print("expected client address:",expectedClientAddress)
                print("actual client address:",self.client_address[0])

                if verifyClientAddress and verifyClientData and verifyPublicKey:
                    username = self.getUsername()
                    
                    doc = {
                    'credential_id': regAuthRequest.get("credential_id"),
                    'publicKey': regAuthRequest.get("public_key")
                    } 
                    userCollection.find_one_and_update({"_id": username}, {"$set":doc})
        
                    self.setChallenge(0) #For at man ikke skal kunne gjennbruke en clientData-hash og dermed endre public key som allerede er satt

                    #Printing for debugging
                    cursor = userCollection.find({"_id":username})
                    for document in cursor:
                        print(document)

                    print("clientAddress:",verifyClientAddress,"clientData:",verifyClientData,"publicKey:",verifyPublicKey)
                    print("SUCCESS! Updated the data for user '%s' in the database" % self.username)
                    print('-'*100)

                    return self.wfile.write(b'Verifikasjon OK. Du kan naa logge inn')
                else:
                    print(verifyClientAddress,verifyClientData,verifyPublicKey)
                    print('-'*100)
                    return self.wfile.write(b'Verifikasjon feilet. ClientData er ikke korrekt')


        #Autentisering
        elif self.path == '/auth':
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            authRequest = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requiredKeys = ["username"]
            checkRequiredKeys = self.requiredKeysInRequest(requiredKeys,authRequest)
            
            if not checkRequiredKeys:
                return self.wfile.write(b'Not all required fields present in request. The required fields are %s' % str(requiredKeys).encode())
            else:    
                userCollection = self.startDatabase()

                username = authRequest.get("username")
                checkUserExistence = userCollection.find_one({'_id': username})
                
                if checkUserExistence == None: #No instance of that username in database
                    return self.wfile.write(b"No user with the username '%s' exists" % username.encode())
                else:
                    userData = userCollection.find_one(username)
                    challenge = self.createChallenge() 
                    self.setChallenge(challenge)
                    self.setUsername(username)

                    credentialID = userData["credential_id"]
                    authResponse = {
                        "rpID": self.rpID,
                        "credential_id": credentialID, 
                        "challenge": challenge 
                    }
                    print("SUCCESS! awaiting signed request")
                    return self.wfile.write(json.dumps(authResponse).encode())
                
        elif self.path == "/auth/verification":
            request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if request == b'': #Hvis body er tom, return 400 bad request
                return self.send_error(400, "Bad request")
            
            requiredKeys = ["client_data", "authenticator_data", "signature"]
            checkRequiredKeys = self.requiredKeysInRequest(requiredKeys,request)

            if checkRequiredKeys:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-type", "application/json")
                self.end_headers()
            else:
                return self.wfile.write(b'Not all required fields present in request')
                
            verifyClientData = sha256(request.get("client_data").encode()).hexdigest() == sha256(str(self.rpID+self.getChallenge()).encode()).hexdigest()
            verifyAuthenticatorData = request.get("authenticator_data") == sha256(str(self.rpID).encode()).hexdigest()
            verifySignature = True#verifySignature(request.get("signature"))
            
            userCollection = self.startDatabase()

            if verifyClientData and verifyAuthenticatorData and verifySignature:
                self.send_response(200, "Verification successful")
                return self.wfile.write(b'SUCCESS! You are now logged in as user %s' % self.getUsername())
            else:
                verificationResponse = {
                    "client_data": verifyClientData,
                    "authenticator_data": verifyAuthenticatorData,
                    "signature": verifySignature 
                }     
                return self.wfile.write(b'Verification failed %s' % json.dumps(verificationResponse).encode())
        else:
            return self.wfile.write(b'%s is not a valid path' % self.path.encode())
        
    def do_OPTIONS(self):
        return self.wfile.write(b'Options respons fungerer')
       
if __name__ == "__main__":
    PORT = 8000
    hostname = socket.gethostname()
    #ip_address = socket.gethostbyname(hostname)
    ip_address = "127.0.0.1"
    # Create an object of the above class
    my_server = socketserver.TCPServer((ip_address, PORT), Handler)
    # Star the server
    print('Server started at ' + ip_address + ':' + str(PORT))
    my_server.serve_forever()

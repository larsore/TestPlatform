import json
import http.server
import socketserver
from typing import Tuple
from http import HTTPStatus
import socket
import numpy as np
import secrets
from routes import routes
import pymongo
from hashlib import sha256



class Handler(http.server.SimpleHTTPRequestHandler):
    challenge = None
    rpID = 1 #TODO skal være en url?
    clientAddress = None

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
        return dbClient, db, userCollection
    
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
            registerRequest = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
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

                dbClient, db, userCollection = self.startDatabase()
              
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
                            "timeout": 30000,
                            "user": {
                                "displayName": username,
                                "id": username
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
            self.data_string = self.rfile.read(int(self.headers['Content-Length']))
            if self.data_string == b'': #Hvis body er tom, return 400 bad request
                return self.send_error(400, "Bad request")
            else:
                self.send_response(HTTPStatus.OK)
                request = json.loads(self.data_string.decode('utf8').replace("'", '"'))
                self.send_header("Content-type", "application/json")
                self.end_headers()


                dbClient, db, userCollection = self.startDatabase()

                """
                dbClient = pymongo.MongoClient(('mongodb://localhost:27017/'))
                db = dbClient['FIDOServer']
                userCollection = db['Users']
                """

                challenge = self.getChallenge()

                expectedClientAddress = self.getClientAddress()

                verifyClientAddress = expectedClientAddress == self.client_address[0]
                #verifyClientAddress = self.client_address[0] == "192.168.0.44" or self.client_address[0] == "127.0.0.1"
                verifyClientData = request.get("client_data") == sha256(str(self.rpID+challenge).encode()).hexdigest()
                verifyPublicKey = "public_key" in request

                print("expected client address:",expectedClientAddress)
                print("actual client address:",self.client_address[0])

                if verifyClientAddress and verifyClientData and verifyPublicKey:
                    username = self.getUsername()
                    """
                    doc = {
                    '_id': username, #TODO krever at kun én bruker registrerer seg og verifiserer seg om gangen. Håndterer ikke flere samtidig
                    'credentialID': request.get("credential_id"),
                    'publicKey': request.get("public_key")
                    } 
                    """#TODO finn ut om det er mulig å legge inn flere fields samtidig i collection

                    userCollection.find_one_and_update({"_id": username}, {"$set": {"credential_id": request.get("credential_id"), "public_key": request.get("public_key")}})

                    cursor = userCollection.find({"_id":username})
                    for document in cursor:
                        print(document)

                    print(verifyClientAddress,verifyClientData,verifyPublicKey)
                    print("SUCCESS! Updated the data for user '%s' in the database" % self.username)
                    print('-'*100)

                    return self.wfile.write(b'Verifikasjon OK. Du kan naa logge inn')
                else:
                    print(sha256(str(self.rpID+self.getChallenge()).encode()).hexdigest())
                    print(verifyClientAddress,verifyClientData,verifyPublicKey)
                    print('-'*100)
                    return self.wfile.write(b'Verifikasjon feilet. ClientData er ikke korrekt')


        #Autentisering
        elif self.path == '/auth':
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.data_string = self.rfile.read(int(self.headers['Content-Length']))

            if self.data_string == b'': 
                self.send_error(400, "Bad Request")
            else:
                dbClient = pymongo.MongoClient(('mongodb://localhost:27017/'))
                db = dbClient['FIDOServer']
                userCollection = db['Users']

                authRequest = json.loads(self.data_string.decode('utf8').replace("'", '"'))
                username = authRequest.get("username")
                checkUserExistence = userCollection.find_one({'_id': username})
                
                if checkUserExistence == None: #No instance of that username in database
                    return self.wfile.write(b"No user with the username '%s' exists" % username.encode())
                else:
                    userData = userCollection.find_one(username)
                    challenge = np.random.randint(0,1000) #TODO generate truly random challenge

                    authResponse = {
                        "rpID": self.rpID,
                        "credential_ID": userData["credentialID"], #TODO denne er ikke lagret i database enda, må gjøres ved registrering
                        "challenge": challenge   
                    }     
                    return self.wfile.write(json.dumps(authResponse).encode())
                    
        else:
            return self.wfile.write(b'%s is not a valid path' % self.path.encode())
       
if __name__ == "__main__":
    PORT = 8000
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    # Create an object of the above class
    my_server = socketserver.TCPServer((ip_address, PORT), Handler)
    # Star the server
    print('Server started at ' + ip_address + ':' + str(PORT))
    my_server.serve_forever()

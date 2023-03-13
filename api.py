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

    def __init__(self, request: bytes, client_address: Tuple[str, int], server: socketserver.BaseServer):
        super().__init__(request, client_address, server)

    #TODO lag truly random challenge
    #TODO funksjoner definert utenfor do_GET/do_POST kan ikke brukes i do_GET/do_POST..
   
    def challenge(self):
        challenge = np.random.randint(0,1000)
        return challenge
    
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
        #Credential creation #TODO dummy data, returner riktige data
        challenge = 5 #TODO kan ikke settes her, må sikre at challenge er fixed mellom første og andre POST request i registrering. 
        rpID = 1 #TODO skal være en nettside
        #Registrering
        if self.path == '/register':
            self.data_string = self.rfile.read(int(self.headers['Content-Length']))
            if self.data_string == b'': #Hvis body er tom, return 400 bad request
                return self.send_error(400, "Bad request")
            else:
                self.send_response(HTTPStatus.OK)
                registerRequest = json.loads(self.data_string.decode('utf8').replace("'", '"'))
                print(registerRequest)
                self.send_header("Content-type", "application/json")
                self.end_headers()

                dbClient = pymongo.MongoClient(('mongodb://localhost:27017/'))
                db = dbClient['FIDOServer']
                userColumn = db['Users']

                username = registerRequest.get("username")
                authenticatorNickname = registerRequest.get("authenticator_nickname")
                checkUserExistence = userColumn.find_one({'_id': username})

                if checkUserExistence == None: #No instance of that username in database
                    doc = {
                        '_id': username,
                        'authenticator_nickname': authenticatorNickname
                    }
                    userColumn.insert_one(doc)

                   

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
                    return self.wfile.write(json.dumps(cred).encode())
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
                print(request)
                self.send_header("Content-type", "application/json")
                self.end_headers()

                
                #if request.httpOrigin == rpID: #TODO finn en måte å hente ut origin fra http request på
                if request.get("client_data") == sha256(str(rpID+challenge).encode()).hexdigest():
                    doc = {
                    '_id': username, #TODO må lagres globalt for å hente ut til verifikasjon
                    'credentialID': request.get("credential_id"),
                    'publicKey': request.get("public_key")
                    } 
                    userColumn.insert_one(doc) #TODO lars: lagre på riktig plass i DB. Usikker på formatering av non-SQL DB
                else:
                    print(sha256(str(rpID+challenge).encode()).hexdigest())
                    return self.wfile.write(b'Verifikasjon feilet. ClientData er ikke korrekt')
            return

        
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
                userColumn = db['Users']

                authRequest = json.loads(self.data_string.decode('utf8').replace("'", '"'))
                username = authRequest.get("username")
                checkUserExistence = userColumn.find_one({'_id': username})
                

                if checkUserExistence == None: #No instance of that username in database
                    return self.wfile.write(b"No user with the username '%s' exists" % username.encode())
                else:
                    userData = userColumn.find_one(username)
                    print(userData)
                    print(type(userData))
                    challenge = np.random.randint(0,1000) #TODO generate challenge

                    authResponse = {
                        "rpID":rpID,
                        "credential_ID": "credID",#userData["credentialID"], #TODO denne er ikke lagret i database enda, må gjøres ved registrering
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

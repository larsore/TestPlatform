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

class Handler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, request: bytes, client_address: Tuple[str, int], server: socketserver.BaseServer):
        super().__init__(request, client_address, server)

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
        #Registrering
        if self.path == '/register':
            self.send_response(HTTPStatus.OK)
            self.data_string = self.rfile.read(int(self.headers['Content-Length']))
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
                regUser = userColumn.insert_one(doc)
                challenge = challenge()
                rpID = self.rpID
                return self.wfile.write(b"Du er naa registrert med brukernavn '%s'" % regUser.inserted_id.encode()) #TODO fjern dette når credential er ferdig laget og returnert
            
                
                #TODO lag challenge, credID
                #TODO returner challenge, credID og rpID
            else:
                #TODO legg til sjekk på username + authenticator? Skal egentil være mulig å registrere seg flere ganger med samme brukernavn men med ny authenticator
                return self.wfile.write(b"Brukernavn '%s' er allerede i bruk, prov med et nytt" % registerRequest.get("username").encode())
        
        
        #Autentisering
        elif self.path == '/auth':
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.data_string = self.rfile.read(int(self.headers['Content-Length']))

            if self.data_string == "": #TODO check if request is malformed
                self.send_response(HTTPStatus.BAD_REQUEST)
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
                    return self.wfile.write(b'Her kommer rpID, credID og challenge')  #TODO return rdID, credID,challenge. CredID ligger i database sammen med brukernavn, ble laget under registrering. 
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

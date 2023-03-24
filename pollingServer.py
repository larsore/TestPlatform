import json
import http.server
import socketserver
from typing import Tuple
from http import HTTPStatus
import socket
from hashlib import sha256
import asyncio

class Handler(http.server.SimpleHTTPRequestHandler):
    

    def __init__(self, request: bytes, client_address: Tuple[str, int], server: socketserver.BaseServer):
        super().__init__(request, client_address, server)

    
    def requiredKeysInRequest(self, requiredKeys, request):
        return all(key in request for key in requiredKeys)

    credentials = { 
        69 : {
            "credential_id": "",
            "rp_id": "rpID",
            "client_data": "dummy data"
        },
        2 : {
            "authenticator_id": 2,
            "credential_id": None,
            "rp_id": None,
            "client_data": None
        },
        3 : {
            "authenticator_id": 3,
            "credential_id": None,
            "rp_id": None,
            "client_data": None
        },
        4 : {
            "authenticator_id": 4,
            "credential_id": None,
            "rp_id": None,
            "client_data": None
        }}
    

    def search_by_credential_id(credentials, credential_id):
        result = []
        for value in credentials.values():
            if value["authenticator_id"] == credential_id:
                result.append(value)
        return result
    
    #GET /authentictor/poll/<authenticatorID>
    def do_GET(self):
        requestedPath = self.path.rsplit('/', 1)[0]
        if requestedPath == "/authenticator/poll":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            newPollingRequest = self.path.rsplit('/', 1)[1]
            print('pollingRequest:',newPollingRequest)

            if newPollingRequest.isdigit():
                if int(newPollingRequest) in self.credentials:
                    authenticatorId = int(newPollingRequest)
                    pollingResponse = self.credentials[authenticatorId] #newPollingRequest = {"credential_id"}
                    del self.credentials[authenticatorId] #remove challenge from dict after sending it to authenticator. 
                    print("Deleted authenticatorID",authenticatorId, "from dictionary")
                    self.wfile.write(json.dumps(pollingResponse).encode())
                    print("Response sent: ", pollingResponse)
                    print("Remaining credentials",self.credentials)
                    print("authneticatorID exists, response sent to authenticator")
                    print('-'*100)
                else:
                    return self.wfile.write(b'No such authneticatorID exists')
            else:
                return self.wfile.write(b'authenticatorID needs to be an integer')
        else:
            self.wfile.write(b"The path %s doesn't exist" % requestedPath.encode)


    
    def do_POST(self):
        # /client/register
        if self.path == "/client/register": #fra client
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            newCredentialRequest = json.loads(self.rfile.read(int(self.headers['Content-Length'])))

            requiredKeys = ["authenticator_id", "rp_id", "client_data", "credential_id"]
            checkRequiredKeys = self.requiredKeysInRequest(requiredKeys,newCredentialRequest)

            if not checkRequiredKeys:
                return self.wfile.write(b'Not all required fields present in request. The required fields are %s' % str(requiredKeys).encode())
            else:   
                if newCredentialRequest["authenticator_id"] in self.credentials:
                    return self.wfile.write(b"Credential with authenticatorId '%s' already exists" % str(authenticatorId).encode())
                else:
                    authenticatorId = newCredentialRequest["authenticator_id"] 
                    del newCredentialRequest["authenticator_id"] 
                    self.credentials[authenticatorId] = newCredentialRequest
                    print("Credential dict: ",self.credentials)
                    print('-'*100)
                    return self.wfile.write(b"Credential for authenticatorID '%s' added to dict" % str(authenticatorId).encode())

        # /client/authenticate
        elif self.path == "/client/authenticate":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            newCredentialRequest = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requiredKeys = ["authenticator_id", "rp_id", "client_data", "credential_id"]
            checkRequiredKeys = self.requiredKeysInRequest(requiredKeys,newCredentialRequest)
            if not checkRequiredKeys:
                return self.wfile.write(b'Not all required fields present in request. The required fields are %s' % str(requiredKeys).encode())
            if not newCredentialRequest["authenticator_id"] in self.credentials:
                return self.wfile.write(b'No credential stored for authenticator with id %s' % str(newCredentialRequest["authenticator_id"]).encode())
            else:
                self.credentials[newCredentialRequest["authenticator_id"]] = newCredentialRequest #legger credential inn i dict
                print(self.credentials)
                print('-'*100)
                return self.wfile.write(b"Credential for authenticatorID '%s' added to dict" % str(newCredentialRequest["authenticator_id"]).encode())
            
        elif self.path == "/authenticator/register" or self.path == "/authenticator/authenticate":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            registerRequest = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            response = {"success": "NS Auth"}
            self.wfile.write(json.dumps(response).encode())
            print("Register request: ",registerRequest)
            print('-'*100)

        
    
if __name__ == "__main__":
    PORT = 8000
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    #ip_address = "192.168.0.51"
    # Create an object of the above class
    my_server = socketserver.TCPServer((ip_address, PORT), Handler)
    # Star the server
    print('Server started at ' + ip_address + ':' + str(PORT))
    my_server.serve_forever()
import json
import http.server
import socketserver
from typing import Tuple
from http import HTTPStatus
import socket
from hashlib import sha256

class Handler(http.server.SimpleHTTPRequestHandler):
    

    def __init__(self, request: bytes, client_address: Tuple[str, int], server: socketserver.BaseServer):
        super().__init__(request, client_address, server)

    
    def requiredKeysInRequest(self, requiredKeys, request):
        return all(key in request for key in requiredKeys)

    challenges = {
        1 : {
            "credential_id": None,
            "rp_id": None,
            "client_data": None
        },
        2 : {
            "credential_id": None,
            "rp_id": None,
            "client_data": None
        }}
    

    """
    def search_by_credential_id(challenges, credential_id):
        result = []
        for key, value in challenges.items():
            if value["credential_id"] == credential_id:
                result.append(value)
        return result
    """
    def search_by_credential_id(challenges, credential_id):
        result = []
        for value in challenges.values():
            if value["credential_id"] == credential_id:
                result.append(value)
        return result
    

    def do_GET(self):
        requestedPath = self.path.rsplit('/', 1)[0]
        if requestedPath == "/polling":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            newPollingRequest = self.path.rsplit('/', 1)[1]
            print('pollingRequest:',newPollingRequest, 'type:',type(newPollingRequest))

            if newPollingRequest.isdigit():
                if int(newPollingRequest) in self.challenges:
                    credId = int(newPollingRequest)
                    pollingResponse = self.challenges[credId] #newPollingRequest = {"credential_id"}
                    del self.challenges[credId] #remove challenge from dict after sending it to authenticator. 
                    self.wfile.write(json.dumps(pollingResponse).encode())
                    print(self.challenges)
                    print("credID exists, response sent to authenticator")
                else:
                    return self.wfile.write(b'No such credentialID exists')
            else:
                return self.wfile.write(b'credentialID needs to be an integer')
        else:
            self.wfile.write(b"The path %s doesn't exist" % requestedPath.encode)


    #/polling/register/

    def do_POST(self):
        if self.path == "/newcredential": #fra client
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            newCredentialRequest = json.loads(self.rfile.read(int(self.headers['Content-Length'])))

            requiredKeys = ["rp_id", "client_data", "credential_id"]
            checkRequiredKeys = self.requiredKeysInRequest(requiredKeys,newCredentialRequest)

            if not checkRequiredKeys:
                return self.wfile.write(b'Not all required fields present in request. The required fields are %s' % str(requiredKeys).encode())
            else:   
                if newCredentialRequest["credential_id"] in self.challenges:
                    return self.wfile.write(b"Credential with credential id '%s' already exists" % str(newCredentialRequest["credential_id"]).encode())
                else:
                    self.challenges[newCredentialRequest["credential_id"]] = newCredentialRequest
                    print(self.challenges)
                    return self.wfile.write(b"Credential '%s' added to dict" % str(newCredentialRequest["credential_id"]).encode())
        else:
            return self.wfile.write(b'No such path exists')
        
    
if __name__ == "__main__":
    PORT = 8000
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    # Create an object of the above class
    my_server = socketserver.TCPServer((ip_address, PORT), Handler)
    # Star the server
    print('Server started at ' + ip_address + ':' + str(PORT))
    my_server.serve_forever()
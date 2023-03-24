import json
import http.server
import socketserver
from typing import Tuple
from http import HTTPStatus
import socket
from hashlib import sha256
import asyncio
import aiohttp

class Handler(http.server.SimpleHTTPRequestHandler):

    ip_address = socket.gethostbyname(socket.gethostname())
    PORT = 8000
    
    

    def __init__(self, request: bytes, client_address: Tuple[str, int], server: socketserver.BaseServer):
        super().__init__(request, client_address, server)

    
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
    

    async def register_credential(self, newCredentialRequest): #client -> pollingServer, registrere nytt credential
        async with aiohttp.ClientSession() as session:
            url = "http://" + self.ip_address + ':' + str(self.PORT) + "/authenticator/register"
            print(url)
            async with session.post(url, json=newCredentialRequest) as response: #sender post til authenticator 
                if response.status == HTTPStatus.OK:
                    result = await response.json()
                    return result
                else:
                    return None
                


    async def do_POST(self):
        if self.path == "/client/register":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            newCredentialRequest = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requiredKeys = ["authenticator_id", "rp_id", "client_data", "credential_id"]
            checkRequiredKeys = self.requiredKeysInRequest(requiredKeys, newCredentialRequest)
            print('1')

            if not checkRequiredKeys:
                return self.wfile.write(b'Not all required fields present in request. The required fields are %s' % str(requiredKeys).encode())
            else:
                print('2')
                if newCredentialRequest["authenticator_id"] in self.credentials:
                    return self.wfile.write(b"Credential with authenticatorId '%s' already exists" % str(authenticatorId).encode())
                else:
                    print('3')
                    authenticatorId = newCredentialRequest["authenticator_id"]
                    del newCredentialRequest["authenticator_id"]
                    self.credentials[authenticatorId] = newCredentialRequest
                    print("Credential dict: ",self.credentials)
                    print('-'*100)

                    result = await self.register_credential(newCredentialRequest)

                    if result:
                        return self.wfile.write(json.dumps(result).encode())
                    else:
                        return self.wfile.write(b"Failed to register credential with the authenticator")
                    

if __name__ == "__main__":
    PORT = 8000
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    #ip_address = "192.168.0.51"
    # Create an object of the above class
    my_server = socketserver.TCPServer((ip_address, PORT), Handler)
    # Star the server
    print('Server started at ' + ip_address + ':' + str(PORT))
    asyncio.run(Handler)
    my_server.serve_forever()
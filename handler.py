import json
import http.server
import socketserver
from typing import Tuple
from http import HTTPStatus
import socket
from hashlib import sha256
import asyncio

from pollingServer import PollingServer

class Handler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, request: bytes, client_address: Tuple[str, int], server: socketserver.BaseServer):
        super().__init__(request, client_address, server)

    def checkKeys(self, requiredKeys, keys):
        if len(requiredKeys) > len(keys):
            return False
        for rKey in requiredKeys:
            if rKey in keys:
                keys.remove(rKey)
        if len(keys) == 0:
            return True
        return False

    def do_GET(self):
        requestedPath = self.path.rsplit('/', 1)[0]
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        if requestedPath == "/authenticator/poll":
            authID = str(self.path.rsplit('/', 1)[1])
            response = PollingServer.handleGETAuthenticator(authID)
            return self.wfile.write(response) 
        else:
            return self.wfile.write(b"The path %s doesn't exist" % requestedPath.encode)


    def do_POST(self):
        # /client/register
        if self.path == "/client/register":
            registerRequest = json.loads(self.rfile.read(int(self.headers['Content-Length'])))

            requiredKeys = ["authenticator_id", "rp_id", "client_data"]

            checkRequiredKeys = self.checkKeys(requiredKeys,list(registerRequest.keys()))


            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            if not checkRequiredKeys:
                return self.wfile.write(b'Not all required fields present in request. The required fields are %s' % str(requiredKeys).encode())

            for key in registerRequest.keys():
                registerRequest[key] = str(registerRequest[key])

            response = PollingServer.handlePOSTClientRegister(registerRequest=registerRequest)
            return self.wfile.write(response)

        # /client/authenticate
        elif self.path == "/client/authenticate":
            authenticateRequest = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            
            requiredKeys = ["authenticator_id", "rp_id", "client_data", "credential_id"]
            
            

            checkRequiredKeys = self.checkKeys(requiredKeys,list(authenticateRequest.keys()))

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            if not checkRequiredKeys:
                return self.wfile.write(b'Not all required fields present in request. The required fields are %s' % str(requiredKeys).encode())

            for key in authenticateRequest.keys():
                authenticateRequest[key] = str(authenticateRequest[key])

            response = PollingServer.handlePOSTClientAuthenticate(authenticateRequest)
            return self.wfile.write(response)

        # /authenticator/register
        elif self.path == "/authenticator/register":
            registerRequest = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            
            if isinstance(registerRequest, list):
                response = PollingServer.handleDismissal(registerRequest, False)
                return self.wfile.write(response)
            
            requiredKeys = ["credential_id", "public_key_t", "public_key_seed", "client_data", "rp_id", "authenticator_id"]
            
            checkRequiredKeys = self.checkKeys(requiredKeys,list(registerRequest.keys()))

            if not checkRequiredKeys:
                return self.wfile.write(b'Not all required fields present in request. The required fields are %s' % str(requiredKeys).encode())

            for key in registerRequest.keys():
                registerRequest[key] = str(registerRequest[key])

            response = PollingServer.handlePOSTAuthenticatorRegister(registerRequest)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            return self.wfile.write(response)

        # /authenticator/authenticate
        elif self.path == "/authenticator/authenticate":
            authenticateRequest = json.loads(self.rfile.read(int(self.headers['Content-Length'])))

            if isinstance(authenticateRequest, list):
                response = PollingServer.handleDismissal(authenticateRequest, True)
                return self.wfile.write(response)

            requiredKeys = ["authenticator_data", "w", "z1", "z2", "c"]
            
            checkRequiredKeys = self.checkKeys(requiredKeys,list(authenticateRequest.keys()))

            if not checkRequiredKeys:
                return self.wfile.write(b'Not all required fields present in request. The required fields are %s' % str(requiredKeys).encode())
            
            response = PollingServer.handlePOSTAuthenticatorAuthenticate(authenticateRequest)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            return self.wfile.write(response)
        else:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            return self.wfile.write(b'No such path exists')
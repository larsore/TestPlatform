import json
import http.server
import socketserver
from typing import Tuple
from http import HTTPStatus
import socket
import numpy as np
import secrets
from routes.routes import routes

class Handler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, request: bytes, client_address: Tuple[str, int], server: socketserver.BaseServer):
        super().__init__(request, client_address, server)

    @property
    def challenge_response(self):
        ch = str(secrets.token_bytes(10))
        challenge = np.random.randint(0,1000)
        return json.dumps({"challenge": challenge}).encode()
    
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
        if self.path == '/register':
            self.send_response(HTTPStatus.OK)
            self.data_string = self.rfile.read(int(self.headers['Content-Length']))
            registerRequest = json.loads(self.data_string.decode('utf8').replace("'", '"'))
            print(registerRequest)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            #TODO check if username already exists. If it exists: return message telling user that it is taken, else: add username to database and return message to user telling that user with username x is successully registered.
            if registerRequest.get("username") not in database:
                return
            return self.wfile.write(b'Du er naa registrert med brukernavn og authenticator %s' % self.data_string)
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

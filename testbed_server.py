import asyncio
import websockets
import numpy as np
import sympy as sy
import struct
from pyfiglet import figlet_format
import time
import sys
from hashlib import sha256
import json

class Verifier:
    def __init__(self):
        self.A = None
        self.clientURL = 'ws://localhost:8765'
        self.q = None
        self.seed = None
        self.n = None
        self.m = None
        self.beta = None
        self.approxBetaInterval = None
        self.t = None
        self.w = None
        self.c = None
        self.z1 = None
        self.z2 = None

    ##Reshape matrix to same dimensions as the one sent by the prover
    def reshapeMatrix(matrix, m):
        return np.reshape(matrix, (-1, m))

#Verification of Az = tc + w
    def verification(self):
        h = sha256()
        h.update(((np.inner(self.A, self.z1) + self.z2 - self.c*self.t)%self.q).tobytes())

        if (h.hexdigest() != self.w):
            print('A*z1 + z2 - c*t != w')
            return False
        elif not (np.all(np.isin(self.z1, self.approxBetaInterval))):
            print('z1 is not short...')
            return False
        elif not (np.all(np.isin(self.z2, self.approxBetaInterval))):
            print('z2 is not short...')
            return False
        else:
            print('SUCCESS')
            return True

    #Trengs én handler per connection
    async def handler(self, websocket):
        while True:
            try:    
                pk = json.loads(await websocket.recv())
                print(type(pk))
                self.seed = pk['seed']
                self.n = pk['n']
                self.m = pk['m']
                self.q = pk['q']
                self.beta = pk['beta']
                self.approxBetaInterval = np.arange(-2*self.beta, 2*self.beta+1)
                np.random.seed(self.seed)

                self.A = np.random.randint(low=0, high=self.q, size=(self.n, self.m))
                self.t = np.asarray(pk['t'], dtype = int)
    
                self.w = await websocket.recv()

                self.c = np.random.randint(-1, 2)
                await websocket.send(str(self.c))

                z = json.loads(await websocket.recv())
                self.z1 = np.asarray(z['z1'], dtype = int)
                self.z2 = np.asarray(z['z2'], dtype = int)

                if self.verification():
                    await websocket.send('SUCCESS')
                else:
                    await websocket.send('FAIL')

            except websockets.ConnectionClosedOK:
                break

            print("Received Matrix A from client : \n" , self.A , "\n")
            print("q from client: ", self.q, "\n")
            print("beta from client: ", self.beta, "\n")
            print("t from client: ", self.t, "\n")
            print("Commitment from clent: ", self.w, "\n")
            print("Opening from client:\n", self.z1, '\n', self.z2)

            print("--------------------------------------------------------------------------------")
            
    async def startServer(self):
        async with websockets.serve(self.handler, "localhost", 8765):
            await asyncio.Future() #server runs until manually stopped

if __name__ == "__main__":
    verifier = Verifier()
    print(figlet_format("SERVER RUNNING"))
    print("Waiting for message from client")          
    asyncio.run(verifier.startServer())




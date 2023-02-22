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
        self.iterations = None
        self.isIterated = False

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
            return True

    #Trengs én handler per connection
    async def handler(self, websocket):
        while True:
            try:    
                pk = json.loads(await websocket.recv())
                self.seed = pk['seed']
                self.n = pk['n']
                self.m = pk['m']
                self.q = pk['q']
                self.beta = pk['beta']
                self.approxBetaInterval = np.arange(-2*self.beta, 2*self.beta+1)
                self.iterations = pk['iterations']
                np.random.seed(self.seed)

                self.A = np.random.randint(low=0, high=self.q, size=(self.n, self.m))
                self.t = np.asarray(pk['t'], dtype = int)
                iteration = 1
                while True:
                    while True:
                        self.w = await websocket.recv()
                        np.random.seed(None)
                        self.c = np.random.randint(-1, 2)
                        await websocket.send(str(self.c))

                        z = json.loads(await websocket.recv())
                        if z['opening'][0] != 'R':
                            print('Successful opening received')
                            self.z1 = np.asarray(z['opening'][0], dtype = int)
                            self.z2 = np.asarray(z['opening'][1], dtype = int)
                            break
                    if iteration != z['iteration']:
                        print('Iterations failed')
                        break
                    elif iteration == self.iterations:
                        print(iteration, ' iterations done\nFINITO!')
                        self.isIterated = True
                        break
                    print(iteration, ' iterations done')
                    iteration += 1

                if self.verification() and self.isIterated:
                    print('SUCCESS')
                    await websocket.send('SUCCESS')
                else:
                    print('FAIL')
                    await websocket.send('FAIL')

            except websockets.ConnectionClosedOK:
                break

                        
    async def startServer(self):
        async with websockets.serve(self.handler, "localhost", 8765):
            await asyncio.Future() #server runs until manually stopped

if __name__ == "__main__":
    verifier = Verifier()
    print(figlet_format("SERVER RUNNING"))
    print("Waiting for message from client")          
    asyncio.run(verifier.startServer())




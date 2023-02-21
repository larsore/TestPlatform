import asyncio
import websockets
import numpy as np
import sympy as sy
import os
from hashlib import sha256
import json
import sys

class Prover:
    def __init__(self, seed, n, q, beta, M, delta):
        self.seed = seed
        np.random.seed(seed)
        self.n = n
        self.q = q
        self.beta = beta
        self.M = M
        self.delta = delta
        self.m = int(np.ceil(np.sqrt(n*np.log(q)/np.log(delta))))
        self.serverURL = 'ws://localhost:8765'
        self.t = None
        self.A = None
        self.s1 = None
        self.s2 = None
        self.y1 = None
        self.y2 = None
        self.c = None
        self.z1 = None
        self.z2 = None
        self.w = None    

    def rejectionSampling(self, z, v, dist):
        # Usikker på om dette er greit hvis vi sampler fra uniform-fordeling og ikke guassian??
        np.random.seed(None)
        u = np.random.rand()
        cond = (1/self.M)*np.exp((-2*(np.inner(z, v)) + np.linalg.norm(v)**2)/(2*dist**2))
        if (u > cond):
            return False
        return True

    #Returnerer parametere nødvendig for å rekonstruere public key
    def genPK(self):
        self.A = np.random.randint(low=0, high=self.q, size=(self.n, self.m))
        np.random.seed(None)
        print(self.A)
        self.s1 = np.random.randint(low=-self.beta, high=self.beta+1, size = self.m)
        np.random.seed(None)
        self.s2 = np.random.randint(low=-self.beta, high=self.beta+1, size = self.n)
        np.random.seed(None)
        self.t = (np.inner(self.A,self.s1) + self.s2)%self.q

    def getW(self):
        np.random.seed(None)
        self.y1 = np.random.randint(low=-self.beta, high=self.beta+1, size=self.m) 
        np.random.seed(None)
        self.y2 = np.random.randint(low=-self.beta, high=self.beta+1, size=self.n)
        self.w = sha256()
        self.w.update(((np.inner(self.A, self.y1) + self.y2)%self.q).tobytes())
        return self.w.hexdigest()

    async def sendPK(self, ws):
        self.genPK()
        await ws.send(json.dumps({'seed': self.seed, 'n': self.n, 'm': self.m, 'q': self.q, 'beta': self.beta, 't': self.t.tolist()}))

    async def sendCommitment(self, ws):
        w = self.getW()
        await ws.send(w)

    async def sendOpening(self, ws):
        print(type(self.c), type(self.s1), type(self.y1))
        self.z1 = self.c*self.s1 + self.y1
        self.z2 = self.c*self.s2 + self.y2
        await ws.send(json.dumps({'z1': self.z1.tolist(), 'z2': self.z2.tolist()}))

    async def runProtocol(self):
        async with websockets.connect(self.serverURL) as websocket:
            await self.sendPK(websocket)
            print('PK sent')
            await self.sendCommitment(websocket)
            print('Commitment sent')
            self.c = int(await websocket.recv())
            print('Challenge received')
            await self.sendOpening(websocket)
            print('Opening sent')
            print(await websocket.recv())

if __name__ == "__main__":
    prover = Prover(seed=int.from_bytes(os.urandom(4), sys.byteorder), n=1280, q=sy.randprime(2**22, 2**(23)-1), beta=2, M=3, delta=1.01)

    while True:
        if input('Wish to start protocol? ') == 'y':
            asyncio.run(prover.runProtocol())
            break


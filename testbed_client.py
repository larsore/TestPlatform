import asyncio
import websockets
import numpy as np
import sympy as sy
import os
from hashlib import sha256
import json
import sys
from getpass import getpass
import time
import matplotlib.pyplot as plt

class Prover:
    def __init__(self, seed, M, delta, n=None, m=None, q=None, beta=None, iterations=None):
        self.seed = seed
        self.n = n
        self.q = q
        self.beta = beta
        self.M = M
        self.delta = delta
        self.m = m
        self.serverURL = 'ws://localhost:8765'
        self.t = None
        self.A = None
        self.s1 = None
        self.s2 = None
        self.y1 = None
        self.y2 = None
        self.z1 = None
        self.z2 = None
        self.w = None   
        self.iterations = iterations
        self.paramPlotData = []
        self.timePlotData = []
        self.testIteration = 1

    def rejectionSampling(self, z, v, dist):
        # Usikker på om dette er greit hvis vi sampler fra uniform-fordeling og ikke guassian??
        np.random.seed(None)
        u = np.random.rand()
        cond = (1/self.M)*np.exp((-2*(np.inner(z, v)) + np.linalg.norm(v)**2)/(2*dist**2))
        if (u > cond):
            return False
        return True

    #Returnerer parametere nødvendig for å rekonstruere public key
    def genPK(self, user):
        np.random.seed(self.seed)
        self.A = np.random.randint(low=0, high=self.q, size=(self.n, self.m))
        np.random.seed(user)
        self.s1 = np.random.randint(low=-self.beta, high=self.beta+1, size = self.m)
        self.s2 = np.random.randint(low=-self.beta, high=self.beta+1, size = self.n)
        #print(self.s1)
        #print(self.s2)
        self.t = (np.inner(self.A,self.s1) + self.s2)%self.q

    def setCommitment(self):
        np.random.seed(None)
        self.y1 = np.random.randint(low=-self.beta, high=self.beta+1, size=self.m) 
        np.random.seed(None)
        self.y2 = np.random.randint(low=-self.beta, high=self.beta+1, size=self.n)
        self.w = sha256()
        self.w.update(((np.inner(self.A, self.y1) + self.y2)%self.q).tobytes())
    
    def getCommitment(self):
        return self.w.hexdigest()

    def getPK(self):
        return {
            'seed': self.seed, 
            'n': self.n, 
            'm': self.m, 
            'q': self.q, 
            'beta': self.beta, 
            't': self.t.tolist(), 
            'iterations': self.iterations
        }

    async def sendPK(self, ws, pk):
        await ws.send(json.dumps(pk))

    async def sendCommitment(self, ws, w):
        await ws.send(w)

    def setOpening(self, c):
        self.z1 = c*self.s1 + self.y1
        self.z2 = c*self.s2 + self.y2
        
    def getOpening(self):
        return self.z1, self.z2
    
    async def sendOpening(self, ws, z1, z2, iteration):
        if not isinstance(z1, str):
            z1 = z1.tolist()
            z2 = z2.tolist()
        await ws.send(json.dumps({'opening': [z1, z2], 'iteration': iteration}))

    async def runProtocol(self, user):
        async with websockets.connect(self.serverURL) as websocket:
            #print(user)
            self.genPK(user=user)
            await self.sendPK(websocket, self.getPK())
            for i in range(1, self.iterations+1):
                while True:
                    self.setCommitment()
                    await self.sendCommitment(websocket, self.getCommitment())
                    c = int(await websocket.recv())
                    self.setOpening(c)
                    checkZ1 = self.rejectionSampling(self.getOpening()[0], c*self.s1, 0.675*np.linalg.norm(c*self.s1))
                    checkZ2 = self.rejectionSampling(self.getOpening()[1], c*self.s2, 0.675*np.linalg.norm(c*self.s2))
                    if checkZ1 and checkZ2:
                        await self.sendOpening(websocket, self.getOpening()[0], self.getOpening()[1], i)
                        break
                    await self.sendOpening(websocket, 'R', 'R', i)
                print(i, ' openings sent')
            result = await websocket.recv()
            print(result)
            if result == 'FAIL':
                print('Iteration no.', self.testIteration, 'failed')
                print('t =', self.t)
                print('w = ', self.w.hexdigest())
                print('A = ', self.A)
                print('z1 =', self.z1)
                print('z2 =', self.z2)
                print()
                print('--------------------------------------------------------')
                print()

    async def testProtocol(self, r, user):
        for val in r:
            self.beta = val
            print(self.q)
            start = time.time()
            await self.runProtocol(user=user)
            stop = time.time()
            self.paramPlotData.append(val)
            self.timePlotData.append((stop-start))
            self.testIteration += 1

if __name__ == "__main__":
    prover = Prover(seed=int.from_bytes(os.urandom(4), sys.byteorder), n=1280, m=1430, q=sy.randprime(2**22, 2**(23)-1), beta=2, M=3, delta=1.01, iterations=100)
    print('Press [1] to login.\nPress [2] to register')
    while True:
        if input('') == '1':
            uname = input('Username: ')
            password = getpass()
            h = sha256()
            h.update((uname+password).encode())
            # Muligens for lite rom med kun de 8 siste bitsa av hash-outputen
            asyncio.run(prover.runProtocol(user=int(h.hexdigest()[-8:], 16)))
            break
"""
    plt.plot(prover.paramPlotData, prover.timePlotData)
    plt.xlabel('beta')
    plt.ylabel('s')
    plt.title('Time spent on completing 1 iteration with beta in [1, 10000]')
    plt.show()
"""
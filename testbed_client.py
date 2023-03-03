import asyncio
import websockets
import numpy as np
from hashlib import sha256
import json
from getpass import getpass
import time
import matplotlib.pyplot as plt

class Prover:
    
    serverURL = 'ws://localhost:8765'

    n = 1280
    m = 1690
    q = 8380417 #23-bit prime
    eta = 5
    gamma = 523776
    #beta = 2
    #approxBetaInterval = np.arange(-2*beta, 2*beta+1)
    #M = 3
    
    paramPlotData = []
    timePlotData = []
    testIteration = 1

    @classmethod
    def getPK(cls, username, secret):
        uhash = int(sha256(username.encode()).hexdigest()[:8], 16)
        np.random.seed(uhash)
        A = np.random.randint(low=0, high=cls.q, size=(cls.n, cls.m))
        sk = cls.genSK(secret=secret)
        t = (np.inner(A, sk['s1']) + sk['s2'])%cls.q
        return {
            'uhash': uhash,
            't': t
        } 

    @classmethod
    def genSK(cls, secret):
        gen = np.random.default_rng(seed = [x for x in secret.encode()])
        s1 = gen.integers(low=-cls.eta, high=cls.eta+1, size = cls.m)
        s2 = gen.integers(low=-cls.eta, high=cls.eta+1, size = cls.n)
        return {
            's1': s1,
            's2': s2
        }

    @classmethod 
    def getCommitment(cls, A):
        np.random.seed(None)
        y1 = np.random.randint(low=-cls.gamma, high=cls.gamma+1, size=cls.m) 
        np.random.seed(None)
        y2 = np.random.randint(low=-cls.gamma, high=cls.gamma+1, size=cls.n)
        w = sha256((((np.inner(A, y1) + y2)%cls.q).tobytes()))
        return {
            'y1': y1,
            'y2': y2,
            'w': w.hexdigest()
        }

    @staticmethod
    def getOpening(s1, s2, y1, y2, c):
        z1 = c*s1 + y1
        z2 = c*s2 + y2
        return {
            'z1': z1,
            'z2': z2,
        }
    
    @staticmethod
    async def sendOpening(ws, iteration=None, opening=None):
        if opening != None:
            z1 = opening[0].tolist()
            z2 = opening[1].tolist()
            await ws.send(json.dumps({'z1': z1, 'z2': z2, 'iteration': iteration}))
        else:
            await ws.send(json.dumps('R'))

    @classmethod
    def rejectionSampling(cls, z, beta):
        # Enkel beta-rejection som vi er usikre på om gjør z og s uavhengige
        if np.all(np.isin(z, np.arange(-(cls.gamma - beta), (cls.gamma - beta)))):
            return True
        return False
        # Rejection sampling ut ifra en Gauss fordeling
        """np.random.seed(None)
        u = np.random.rand()
        cond = (1/cls.M)*np.exp((-2*(np.inner(z, v)) + np.linalg.norm(v)**2)/(2*dist**2))
        if (u > cond):
            return False
        return True"""

    @classmethod
    async def negotiate(cls):
        async with websockets.connect(cls.serverURL) as ws:
            await ws.send()
    
    @classmethod
    async def authenticate(cls, username, secret):
        async with websockets.connect(cls.serverURL) as websocket:
            # Let server know that you are going to authenticate
            await websocket.send(json.dumps('A'))
            await websocket.send(json.dumps(username))
            pk = cls.getPK(username=username, secret=secret)
            np.random.seed(pk['uhash'])
            A = np.random.randint(low=0, high=cls.q, size=(cls.n, cls.m))
            sk = cls.genSK(secret=secret)      
            iterations = json.loads(await websocket.recv()) #Integritetssjekk på dette for å forsikre at en MitM ikke har endret verdien
            if not isinstance(iterations, str):
                counter = 0
                a = 0
                for i in range(1, iterations+1):
                    while True:
                        counter += 1
                        commitment = cls.getCommitment(A=A)
                        await websocket.send(commitment['w'])
                        print('Commitment w =', commitment['w'], 'sent')
                        c = json.loads(await websocket.recv())
                        print('Challenge c =', c, 'received')
                        if not isinstance(c, str):
                            opening = cls.getOpening(sk['s1'], sk['s2'], commitment['y1'], commitment['y2'], c)
                            checkZ1 = cls.rejectionSampling(opening['z1'], beta=cls.eta)
                            checkZ2 = cls.rejectionSampling(opening['z2'], beta=cls.eta)
                            if checkZ1 and checkZ2:
                                a += 1
                                print('Accepted!')
                                await cls.sendOpening(websocket, iteration=i, opening=[opening['z1'], opening['z2']])
                                print(opening['z1'])
                                print(opening['z2'])
                                print()
                                print('Opening sent')
                                break
                            await cls.sendOpening(websocket)
                            print('Rejected!')
                        else:
                            return
                    print(i, ' openings sent')
                result = await websocket.recv()
                print(result)
                print(a/counter)
                                 
            else:
                print(iterations)

    @classmethod
    async def register(cls, username, secret):
        #if len(secret) < 8:
        #    print('Secret cannot be shorter than 8 characters')
        #    return
        # Let server know that you are going to register
        async with websockets.connect(cls.serverURL) as websocket:
            await websocket.send(json.dumps('R'))
            pk = cls.getPK(username=username, secret=secret)
            await websocket.send(json.dumps({
                'seed': pk['uhash'],
                't': pk['t'].tolist(),
                'uname': username
            }))
            print(json.loads(await websocket.recv()))

   

if __name__ == "__main__":
        
    prover = Prover()
    #prover.negotiate()

    while True:
        print('Press [1] to login.\nPress [2] to register')
        choice = input('')
        
        uname = input('Username: ')
        secret = input('Secret: ')
        # Muligens for lite rom med kun de 8 siste bitsa av hash-outputen

        if choice == '1':
            asyncio.run(prover.authenticate(username=uname, secret=secret))
        
        elif choice == '2':
            asyncio.run(prover.register(username=uname, secret=secret))
        

"""
    plt.plot(prover.paramPlotData, prover.timePlotData)
    plt.xlabel('beta')
    plt.ylabel('s')
    plt.title('Time spent on completing 1 iteration with beta in [1, 10000]')
    plt.show()
"""
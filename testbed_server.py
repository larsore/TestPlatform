import asyncio
import websockets
import numpy as np
import sympy as sy
from pyfiglet import figlet_format
from hashlib import sha256
import json
import pymongo


class Verifier:

    dbClient = pymongo.MongoClient(('mongodb://localhost:27017/'))
    db = dbClient['TestplatformDatabase']
    userCol = db['Users']

    n = 1280
    m = 1690
    q = 4002909139 # 32-bit prime
    beta = 2
    approxBetaInterval = np.arange(-2*beta, 2*beta+1)

    isIterated = False
    authenticated = False
    iterations = None

    @classmethod
    def __init__(cls, iterations):
        cls.iterations = iterations
        
    @classmethod
    def verification(cls, A, t, z1, z2, c, w):
        h = sha256()
        h.update(((np.inner(A, z1) + z2 - c*t)%cls.q).tobytes())

        if (h.hexdigest() != w):
            print()
            return {
                'result': False,
                'reason': 'A*z1 + z2 - c*t != w'
            }
        elif not (np.all(np.isin(z1, cls.approxBetaInterval))):
            print()
            return {
                'result': False,
                'reason': 'z1 is not short...' 
            }
        elif not (np.all(np.isin(z2, cls.approxBetaInterval))):
            print()
            return {
                'result': False,
                'reason': 'z2 is not short...'
            }
        else:
            return {
                'result': True,
                'reason': 'You know the secret'
            }

    @classmethod
    async def handleRegister(cls, ws):
        regData = json.loads(await ws.recv())
        checkUser = cls.userCol.find_one({
            '_id': regData['uname']
        })
        if checkUser == None:
            doc = {
                '_id': regData['uname'],
                't': regData['t'],
                'seed': regData['seed']
            }
            regUser = cls.userCol.insert_one(doc)
            print(regUser.inserted_id + ' was successfully registered!')
            await ws.send(json.dumps(regUser.inserted_id + ' was successfully registered!'))
        else:
            print(regData['uname'] + ' already exists in DB')
            await ws.send(json.dumps('A user with the username "'+ regData['uname'] + '" already exists'))

    @classmethod
    async def handleAuth(cls, ws):
        uname = json.loads(await ws.recv())
        user = cls.userCol.find_one({
            '_id': uname
        })
        if user != None:
            np.random.seed(user['seed'])
            A = np.random.randint(low=0, high=cls.q, size=(cls.n, cls.m))
            t = np.asarray(user['t'], dtype = int)
            await ws.send(json.dumps(cls.iterations))
            iteration = 1
            while True:
                while True:
                    w = await ws.recv()
                    print('Commitment w = ', w, 'received')
                    np.random.seed(None)
                    c = np.random.randint(low=-1, high=2)
                    print('Challenge c =',c, 'drawn')
                    await ws.send(json.dumps(c))

                    opening = json.loads(await ws.recv())
                    if opening != 'R':
                        z1 = np.asarray(opening['z1'], dtype = int)
                        z2 = np.asarray(opening['z2'], dtype = int)
                        print('Opening received')
                        verified = cls.verification(A=A, t=t, z1=z1, z2=z2, c=c, w=w)
                        if not verified['result']:
                            print('Opening NOT accepted')
                            await ws.send(json.dumps('Authentication failed'))
                            raise StopIteration(verified['reason'])
                        print('Opening accepted')
                        break
                
                if iteration != opening['iteration']:
                    print('Iterations failed')
                    break
                elif iteration == cls.iterations:
                    print(iteration, ' iterations done')
                    cls.isIterated = True
                    cls.authenticated = True
                    break
                print(iteration, ' iterations done')
                iteration += 1

            if cls.authenticated and cls.isIterated:
                print('SUCCESS')
                await ws.send('SUCCESS')
            else:
                await ws.send('FAIL')
                
        else:
            print('Failed login attempt on un-registered user')
            await ws.send(json.dumps(uname+' has not been registered'))

    #Trengs én handler per connection
    @classmethod
    async def handler(cls, ws):
        while True:
            try:
                action = json.loads(await ws.recv())
                if action == 'R':
                    await cls.handleRegister(ws)
                else:
                    await cls.handleAuth(ws)
                

            except websockets.ConnectionClosedOK:
                break

    @classmethod                    
    async def startServer(cls):
        async with websockets.serve(cls.handler, "localhost", port=8765):
            await asyncio.Future() #server runs until manually stopped

if __name__ == "__main__":
    verifier = Verifier(iterations=100)
    print(figlet_format("SERVER RUNNING"))
    print("Waiting for message from client")          
    asyncio.run(verifier.startServer())




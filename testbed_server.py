import asyncio
import websockets
import numpy as np
import sympy as sy
from pyfiglet import figlet_format
from hashlib import sha256
import json
import pymongo


class Verifier:
    def __init__(self, iterations):
        dbClient = pymongo.MongoClient(('mongodb://localhost:27017/'))
        db = dbClient['TestplatformDatabase']
        self.userCol = db['Users']

        self.n = 1280
        self.m = 1690
        self.q = 4002909139 # 32-bit prime
        self.beta = 2
        self.approxBetaInterval = np.arange(-2*self.beta, 2*self.beta+1)

        self.iterations = iterations
        self.isIterated = False
        self.authenticated = False

        

        
#Verification of Az = tc + w
    def verification(self, A, t, z1, z2, c, w):
        h = sha256()
        h.update(((np.inner(A, z1) + z2 - c*t)%self.q).tobytes())

        if (h.hexdigest() != w):
            print()
            return {
                'result': False,
                'reason': 'A*z1 + z2 - c*t != w'
            }
        elif not (np.all(np.isin(z1, self.approxBetaInterval))):
            print()
            return {
                'result': False,
                'reason': 'z1 is not short...' 
            }
        elif not (np.all(np.isin(z2, self.approxBetaInterval))):
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

    async def handleRegister(self, ws):
        regData = json.loads(await ws.recv())
        checkUser = self.userCol.find_one({
            '_id': regData['uname']
        })
        if checkUser == None:
            doc = {
                '_id': regData['uname'],
                't': regData['t'],
                'seed': regData['seed']
            }
            regUser = self.userCol.insert_one(doc)
            print(regUser.inserted_id + ' was successfully registered!')
            await ws.send(json.dumps(regUser.inserted_id + ' was successfully registered!'))
        else:
            print(regData['uname'] + ' already exists in DB')
            await ws.send(json.dumps('A user with the username "'+ regData['uname'] + '" already exists'))


    async def handleAuth(self, ws):
        uname = json.loads(await ws.recv())
        user = self.userCol.find_one({
            '_id': uname
        })
        if user != None:
            np.random.seed(user['seed'])
            A = np.random.randint(low=0, high=self.q, size=(self.n, self.m))
            t = np.asarray(user['t'], dtype = int)
            await ws.send(json.dumps(self.iterations))
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
                        verified = self.verification(A=A, t=t, z1=z1, z2=z2, c=c, w=w)
                        if not verified['result']:
                            print('Opening NOT accepted')
                            await ws.send(json.dumps('Authentication failed'))
                            raise StopIteration(verified['reason'])
                        print('Opening accepted')
                        break
                
                if iteration != opening['iteration']:
                    print('Iterations failed')
                    break
                elif iteration == self.iterations:
                    print(iteration, ' iterations done')
                    self.isIterated = True
                    self.authenticated = True
                    break
                print(iteration, ' iterations done')
                iteration += 1

            if self.authenticated and self.isIterated:
                print('SUCCESS')
                await ws.send('SUCCESS')
            else:
                await ws.send('FAIL')
                
        else:
            print('Failed login attempt on un-registered user')
            await ws.send(json.dumps(uname+' has not been registered'))

    #Trengs én handler per connection
    async def handler(self, ws):
        while True:
            try:
                action = json.loads(await ws.recv())
                if action == 'R':
                    await self.handleRegister(ws)
                else:
                    await self.handleAuth(ws)
                

            except websockets.ConnectionClosedOK:
                break

                        
    async def startServer(self):
        async with websockets.serve(self.handler, port=8765):
            await asyncio.Future() #server runs until manually stopped

if __name__ == "__main__":
    verifier = Verifier(iterations=100)
    print(figlet_format("SERVER RUNNING"))
    print("Waiting for message from client")          
    asyncio.run(verifier.startServer())




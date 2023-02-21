import asyncio
import websockets
import numpy as np
import sympy as sy
import struct
from hashlib import sha256

server = "ws://localhost:8765"

"""
q = sy.randprime(2**31, 2**(32)-1)
m = 4 #kolonner
n = 12 #rader
beta = 30
"""

seed = 0
np.random.seed(seed)

q = sy.randprime(2**22, 2**(23)-1)
n = 1280
beta = 2
M = 3
delta = 1.01
m = int(np.ceil(np.sqrt(n*np.log(q)/np.log(delta))))

a = input('Wish to start protocol? ')

#Convert vectors and matrices to binary 

def toBinary(data):
    if type(data) is np.ndarray: #if vector or matrix
        binaryData = data.tobytes()
    else:
        binaryData = struct.pack('%sl' % len(data), *data)
    return binaryData


#Prover generates A and secret s
A = np.random.randint(low=0, high=q, size=(n, m))
s1 = np.random.randint(low=-beta, high=beta+1, size = m)
s2 = np.random.randint(low=-beta, high=beta+1, size = n)
t = (np.inner(A,s1) + s2)%q

y1 = np.random.randint(low=-beta, high=beta+1, size=m) 
y2 = np.random.randint(low=-beta, high=beta+1, size=n)
w = sha256()
w.update(((np.inner(A, y1) + y2)%q).tobytes())

async def onMessage():
    async with websockets.connect(server) as websocket:
        
        print('A = \n', A, "\n")

        await websocket.send(str(seed))
        print("Sent seed = \n", str(seed),"\n")

        await websocket.send(str(n))
        print("Sent n: ", str(n), "\n")
        
        await websocket.send(str(m))
        print("Sent m: ", str(m), "\n")

        await websocket.send(str(q))
        print("Sent q: ", str(q), "\n")

        await websocket.send(str(beta))
        print("Sent beta: ", str(beta), "\n")

        await websocket.send(toBinary(t))
        print("Sent t = ", t,"\n")

        await websocket.send(w.hexdigest())
        print("Sent w = ", w.hexdigest(),"\n")

        challenge = await websocket.recv()
        print("Received challenge from server: ", challenge,"\n")

        z1 = (int(challenge)*s1 + y1)
        z2 = (int(challenge)*s2 + y2)
        
        await websocket.send(toBinary(z1))
        print("sent z1: ", z1,"\n")

        await websocket.send(toBinary(z2))
        print("sent z2: ", z2,"\n")

        result = await websocket.recv()
        print("Received result from server: ", result,"\n")

        print("--------------------------------------------------------------------------------")
        
if a == 'y':
    asyncio.run(onMessage())

import asyncio
import websockets
import numpy as np
import sympy as sy
import struct

server = "ws://localhost:8765"

q = sy.randprime(2**31, 2**(32)-1)
m = 4 #rader
n = 12 #kolonner
beta = 30


#Convert vectors and matrices to binary 

def toBinary(data):
    if type(data) is np.ndarray: #if vector or matrix
        binaryData = data.tobytes()
    else:
        binaryData = struct.pack('%sl' % len(data), *data)
    return binaryData


#Prover generates A and secret s
A = np.random.randint(low=0, high=q, size=(n, m))
s = np.random.randint(low=-1, high=2, size = m)

#Convert matrix A to binary for sending to server
binaryA = toBinary(A)


#Prover calculates public key t
t = (A.dot(s))%q
binaryT = toBinary(t)


y = np.random.randint(low=-1, high=2, size=m)

#Committment w
w = (A.dot(y))%q
binaryW = toBinary(w)




async def onMessage():
    async with websockets.connect(server) as websocket:
        
        await websocket.send(binaryA)
        print("Sent A = \n", str(A),"\n")

        await websocket.send(str(m))
        print("Sent m: ", m, "\n")

        await websocket.send(binaryT)
        print("Sent t = ", t,"\n")

        await websocket.send(binaryW)
        print("Sent w = ", w,"\n")

        challenge = await websocket.recv()
        print("Received challenge from server: ", challenge,"\n")

        z = (s*int(challenge) + y)
        binaryZ = toBinary(z)
        await websocket.send(binaryZ)
        print("sent z: ", z,"\n")

        print("--------------------------------------------------------------------------------")
        
       
    

asyncio.run(onMessage())

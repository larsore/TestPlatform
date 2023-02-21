import asyncio
import websockets
import numpy as np
import sympy as sy
import struct
from pyfiglet import figlet_format
import time
import sys
from hashlib import sha256


print(figlet_format("SERVER RUNNING"))
print("waiting for message from client")


client = "ws://localhost:8765"


q = sy.randprime(2**31, 2**(32)-1)

"""
def unpack(binary_data):
    # convert binary data to float values
    integer_values = struct.unpack('%sl' % len(binary_data)//4, binary_data)

    # convert float values to a list
    data = list(integer_values)

    return data


def unpack_vector(binary_vector, dtype=np.int32):
    '''unpack binary representation of a vector into a numpy array'''
    size = len(binary_vector) // struct.calcsize(dtype)
    return np.array(struct.unpack(f'{size}{dtype.char}', binary_vector), dtype=dtype)

def unpack_matrix(binary_matrix, dtype=np.int32, shape=None):
    '''unpack binary representation of a matrix into a numpy array'''
    if shape is None:
        raise ValueError('shape must be specified')
    rows, cols = shape
    size = rows * cols
    binary_vector = struct.unpack(f'{size}{dtype.any}', binary_matrix)
    return np.array(binary_vector, dtype=dtype).reshape(shape)
"""

##Reshape matrix to same dimensions as the one sent by the prover
def reshapeMatrix(matrix,m):
    subarrayLength = m
    matrix = np.reshape(matrix, (-1, subarrayLength))
    return matrix

#Verification of Az = tc + w
def verification(A,z1,z2,t,c,w,q,approxBetaInterval):
    h = sha256()
    h.update(((np.inner(A, z1) + z2 - c*t)%q).tobytes())

    if (h.hexdigest() != w):
        print('A*z1 + z2 - c*t != w')
        return False
    elif not (np.all(np.isin(z1, approxBetaInterval))):
        print('z1 is not short...')
        return False
    elif not (np.all(np.isin(z2, approxBetaInterval))):
        print('z2 is not short...')
        return False
    else:
        print('SUCCESS')
        return True
    
        

#Trengs én handler per connection
async def handler(websocket):
    while True:
        try:    
            seed = int(await websocket.recv())
            n = int(await websocket.recv())
            m = int(await websocket.recv())
            q = int(await websocket.recv())
            beta = int(await websocket.recv())
            approxBetaInterval = np.arange(-2*beta, 2*beta+1)

            np.random.seed(seed)

            A = np.random.randint(low=0, high=q, size=(n, m))
 
            binaryT = await websocket.recv()
            t = np.frombuffer(binaryT, dtype = int)

            w = await websocket.recv()

            c = np.random.randint(-1,2)
            await websocket.send(str(c))

            binaryZ1 = await websocket.recv()
            binaryZ2 = await websocket.recv()

            z1 = np.frombuffer(binaryZ1, dtype = int)
            z2 = np.frombuffer(binaryZ2, dtype = int)

            if verification(A,z1,z2,t,c,w,q,approxBetaInterval):
                await websocket.send('SUCCESS')
            else:
                await websocket.send('FAIL')

        except websockets.ConnectionClosedOK:
            break

        print("Received Matrix A from client : \n" ,A , "\n")
        print("m from client: ", m, "\n")
        print("q from client: ", q, "\n")
        print("beta from client: ", beta, "\n")
        print("t from client: ", t, "\n")
        print("w from clent: ", w, "\n")
        print("z1 from client: ", z1)
        print("z2 from client: ", z2)

        print("--------------------------------------------------------------------------------")
        

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future() #server runs until manually stopped


if __name__ == "__main__":
    asyncio.run(main())




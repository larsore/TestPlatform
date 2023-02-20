import asyncio
import websockets
import numpy as np
import sympy as sy
import struct

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


def reshapeMatrix(matrix,m):
    subarrayLength = m
    matrix = np.reshape(matrix, (-1, subarrayLength))
    return matrix



def verification(A,z,t,c,w,q):
    leftSide = (A.dot(z))%q
    rightSide = (t*c+w)%q

    if np.array_equal(leftSide, rightSide):
        print("JA!")

    if (rightSide.any() != leftSide.any()):
        raise ValueError('Az != t*c + w')
    else: 
        print("SUCCESS")

#Trengs én handler per connection
async def handler(websocket):
    while True:
        try:    
            binaryA = await websocket.recv()
            A = np.frombuffer(binaryA, dtype = int)
            A = reshapeMatrix(A,4)

            m = await websocket.recv()
            m = int(m)

            binaryT = await websocket.recv()
            t = np.frombuffer(binaryT, dtype = int)

            binaryW = await websocket.recv()
            w = np.frombuffer(binaryW, dtype = int)

            c = np.random.randint(0,q-1)
            await websocket.send(str(c))

            binaryZ = await websocket.recv()
            z = np.frombuffer(binaryZ, dtype = int)

        except websockets.ConnectionClosedOK:
            break

        print("Received Matrix A from client : \n" ,A , "\n")
        print("m from client: ", m, "\n")
        print("t from client: ", t, "\n")
        print("w from clent: ", w, "\n")
        print("z from client: ", z)

        verification(A,z,t,c,w,q)
        




async def main():
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future() #server runs until manually stopped




if __name__ == "__main__":
    asyncio.run(main())




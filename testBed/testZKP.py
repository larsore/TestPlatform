import numpy as np
import sympy as sy
from hashlib import sha256

q = sy.randprime(2**22, 2**(23)-1)
n = 1280
m = 23000
beta = 2
betaInterval = np.arange(-beta, beta+1)
M = 3

# Peggy generates A and secret s

A = np.random.randint(low=0, high=q, size=(n, m))
s1 = np.random.randint(low=-beta, high=beta+1, size = m)
s2 = np.random.randint(low=-beta, high=beta+1, size = n)

# Peggy calculates lattice-point t which works as her identification

t = (np.inner(A,s1) + s2)%q

# Algorithm used to either reject or accept opening z based on whether or not secret s and z are independent

def rejectionSampling(z, v, dist):
    # Usikker på om dette er greit hvis vi sampler fra uniform-fordeling og ikke guassian??
    u = np.random.rand()
    cond = (1/M)*np.exp((-2*(np.inner(z, v)) + np.linalg.norm(v)**2)/(2*dist**2))
    if (u > cond):
        return False
    return True

# Sample commitment w = Ay, receive random challenge c and perform rejection sampling on opening z until algorithm 'accepts'

i = 1
sd = 0.275*np.linalg.norm(s1)
step = 5
while True:
    y1 = (np.rint(np.random.normal(0, sd, m))).astype(int)
    #y1 = np.random.randint(low=-beta, high=beta+1, size=m) 
    y2 = (np.rint(np.random.normal(0, sd, n))).astype(int)
    print(y1)
    #y2 = np.random.randint(low=-beta, high=beta+1, size=n) 
    w = sha256()
    w.update(((np.inner(A, y1) + y2)%q).tobytes())
    c = np.random.randint(low=-beta, high=beta+1)
    z1 = (c*s1 + y1)
    z2 = (c*s2 + y2)
    rejection1 = rejectionSampling(z1, c*s1, sd)
    rejection2 = rejectionSampling(z2, c*s2, sd)
    checkNorm = ((np.all(np.isin(z1, betaInterval))) and (np.all(np.isin(z2, betaInterval))))
    print(i, rejection1, rejection2, checkNorm)
    i+=1
    print(sd)
    if sd < 5:
        step = 0.1
    sd -= step
    if rejection1 and rejection2 and checkNorm:
        break

# Victor verifies
h = sha256()
h.update(((np.inner(A, z1) + z2 - c*t)%q).tobytes())

if (h.digest() != w.digest()):
    raise ValueError('A*z1 + z2 - ct is NOT EQUAL to w')
elif not (np.all(np.isin(z1, betaInterval))):
    raise ValueError('z1 is not short...')
elif not (np.all(np.isin(z2, betaInterval))):
    raise ValueError('z2 is not short...')
else:
    print('SUCCESS')
import numpy as np
from hashlib import sha256

n = 1280
m = 1690
q = 4002909139 # 32-bit prime
beta = 2
M = 3
A = np.random.randint(low=0, high=q, size=(n, m))

def rejectionSampling(z, v, dist):
        # Usikker på om dette er greit hvis vi sampler fra uniform-fordeling og ikke guassian??
        np.random.seed(None)
        u = np.random.rand()
        cond = (1/M)*np.exp((-2*(np.inner(z, v)) + np.linalg.norm(v)**2)/(2*dist**2))
        if (u > cond):
            return False
        return True

def getCommitment(A):
        np.random.seed(None)
        y1 = np.random.randint(low=-beta, high=beta+1, size=m) 
        #y1 = np.asarray([1 for i in range(self.m)])
        np.random.seed(None)
        y2 = np.random.randint(low=-beta, high=beta+1, size=n)
        #y2 = np.asarray([1 for i in range(self.n)])
        w = sha256((((np.inner(A, y1) + y2)%q).tobytes()))
        return {
            'y1': y1,
            'y2': y2,
            'w': w.hexdigest()
        } 
    
def getOpening(s1, s2, y1, y2, c):
        z1 = c*s1 + y1
        z2 = c*s2 + y2
        return {
            'z1': z1,
            'z2': z2,
        }

def getPK(username, secret):
        uhash = int(sha256(username.encode()).hexdigest()[:8], 16)
        secretHash = int(sha256((secret).encode()).hexdigest()[:8], 16)
        np.random.seed(uhash)
        
        np.random.seed(secretHash)
        s1 = np.random.randint(low=-beta, high=beta+1, size = m)
        s2 = np.random.randint(low=-beta, high=beta+1, size = n)
        t = (np.inner(A, s1) + s2)%q
        return {
            'uhash': uhash,
            'secretHash': secretHash,
            't': t,
            's1': s1,
            's2': s2
        }

username = 'vegard'
secret = 'v'

pk = getPK(username=username, secret=secret)

c = -1

accept = 0

for i in range(1000):
    com = getCommitment(A=A)
    ope = getOpening(s1=pk['s1'], s2=pk['s2'], y1=com['y1'], y2=com['y2'], c=c)
    checkZ1 = rejectionSampling(ope['z1'], c*pk['s1'], 0.675*np.linalg.norm(c*pk['s1']))
    checkZ2 = rejectionSampling(ope['z2'], c*pk['s2'], 0.675*np.linalg.norm(c*pk['s2']))
    if checkZ1 and checkZ2:
        accept += 1

print(accept)
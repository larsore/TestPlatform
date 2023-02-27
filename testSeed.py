import numpy as np

np.random.seed(None)
t=0
for i in range(1000):
    c = np.random.randint(low=-1, high=2)
    if c == 0:
        t += 1

print(t)
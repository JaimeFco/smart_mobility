import pandas as pd
import os
import numpy as np
import collections
import sys

"""
This program receive as arguments:
    - Name of the .npy file where the OD matrices are allocated
    - Start index to make the VMR matrices
    - End index (exclusive) to make the VMR matrices

The program writes as many txt as required in the current directory.
"""

def convertToVMR(M, start=None, end=None):
    if start == None:
        start = 0
    if end == None:
        end = M.shape[0]

    hours = [0, 6, 12, 18]
    # Open file
    for k in range(start, end):
        fout = open("OD_output{0}.txt".format(k),'w')
        # Format header
        fout.write("$VMR\n")
        fout.write("1\n")
        fout.write("{0:02d}:00 {1:02d}:00\n".format(hours[k%4], hours[k%4]+6))
        # District numbers
        for i in range(M.shape[1]):
            fout.write("{0:4d}".format(i+1))
        fout.write("\n")
        # Save adj matrix
        np.savetxt(fout, M[k], delimiter='    ', fmt = '%i')
        fout.close()


## Read nunpy array
M = np.load(sys.argv[1])
convertToVMR(M, int(sys.argv[2]), int(sys.argv[3]))

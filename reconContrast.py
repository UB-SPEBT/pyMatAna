import sys
import math
import numpy as np
import struct
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.animation as animation
from matplotlib.animation import FuncAnimation
import rich.progress
import json 

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TaskProgressColumn,
)

# Matrix dimension 90*90*32*6*8
with open('../SysMatConfig/Parameters.json') as json_file:
    parameters = json.load(json_file)

NImgX_ = parameters["numImageX"]
NImgY_ = parameters["numImageY"]
NDetY_ = parameters["pixelSiPM"]
NModule_ = parameters["numPanel"]
NDetX_ = parameters["numDetectorLayer"]


# Open the file.
sysmatPath = parameters["sysmatPath"]
inFname = 'sysmatMatrix.sysmat'
dataSize = NImgX_*NImgY_*NDetY_*NModule_*NDetX_
filePath = sysmatPath+inFname

with rich.progress.open(filePath, 'rb') as inF:
    # Read in the matrix
    dataUnpack = np.asarray(struct.unpack('f'*dataSize, inF.read(dataSize*4)))
    # Reshape the 5D array into a 2D matrix
    dataMatrix = dataUnpack.reshape((NDetX_ * NModule_*NDetY_, NImgX_*NImgY_))

print("Complete Read-in Data!")
imgTemplate = np.zeros((NImgX_, NImgY_))
print("{:>28}:\t{:}".format("Read-in System Matrix Shape", dataMatrix.shape))

# Remove zero rows from the matrix
sysMatrix = dataMatrix[~np.all(dataMatrix == 0, axis=1)]
print("{:>28}:\t{:}".format("Reduced System Matrix Shape", sysMatrix.shape))

# Read in the phantom
addNoise = parameters["AddPoisson"]
if addNoise:
    inFname = '../ImageReconstructor/input/circle-phantom_noise.npz'
else:
    inFname = '../ImageReconstructor/input/circle-phantom.npz'

dataUnpack = np.load(inFname)
dataSize = NImgX_*NImgY_
phantom = dataUnpack['arr_0'].reshape((NImgX_, NImgY_))

# Calculate forward projection
projection = np.matmul(sysMatrix, phantom.flatten())
print("{:>28}:\t{:}".format("Projection Shape", projection.shape))

# Implementation of the recursive Maximum-Likelihood Expectation-
# Maximization (ML-EM) algorithm.


def backwardProj(lastArr, projArr, sysMat):
    forwardLast = np.matmul(sysMat, lastArr)
    quotients = projArr/forwardLast
    return np.matmul(quotients, sysMat)/np.sum(sysMat, axis=0)*lastArr

# Calculate region map


# bgIndex = np.nonzero(phantom.flatten() == bg)
# objIndex = []
# for idx in range(0, 6):
#     objIndex.append(np.nonzero(regionMapFlat == values[idx]))

# Iterate for 5000 times, start from a flat image with all ones.
NIteration = parameters["ReconstructionIterations"]
reconImg = np.ones(NImgX_*NImgY_)

# print('Numerator: ',(np.mean(reconImg[objIndex[0]])-np.mean(reconImg[bgIndex])))
# print('Denominator: ',np.std(reconImg[bgIndex]))

progress = Progress(
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    # TaskProgressColumn(),
    "{task.completed}/{task.total}",
    TimeRemainingColumn(),
)
scale = 100
# CNR = np.zeros((6, NIteration//scale))
storedReconImg = np.zeros((NIteration//scale, NImgX_*NImgY_))
with progress:
    progress.console.print("Iterative reconstruction calculation...")
    task1 = progress.add_task("Iteration:", total=NIteration)
    for iter in range(NIteration):
        reconImg = backwardProj(reconImg, projection, sysMatrix)
        progress.advance(task1)
        if iter % scale == 0:
            storedReconImg[iter//scale] = reconImg
            # for idx in range(0, 6):
            #     numerator=np.mean(reconImg[objIndex[0]])-np.mean(reconImg[bgIndex])
            #     denominator=np.std(reconImg[bgIndex])
            #     CNR[idx, iter//scale]=numerator/denominator


outFname = 'images/contrast-recon-data.npz'
np.savez(outFname, storedReconImg.astype(np.float32))
import sys

import numpy as np
import ripser
import scipy.sparse
import vtk
from vtk.numpy_interface import dataset_adapter as dsa


def lower_star_img(img):
    m, n = img.shape

    idxs = np.arange(m * n).reshape((m, n))

    I = idxs.flatten()
    J = idxs.flatten()
    V = img.flatten()

    # Connect 8 spatial neighbors
    tidxs = np.ones((m + 2, n + 2), dtype=np.int64) * np.nan
    tidxs[1:-1, 1:-1] = idxs

    tD = np.ones_like(tidxs) * np.nan
    tD[1:-1, 1:-1] = img

    for di in [-1, 0, 1]:
        for dj in [-1, 0, 1]:

            if di == 0 and dj == 0:
                continue

            thisJ = np.roll(np.roll(tidxs, di, axis=0), dj, axis=1)
            thisD = np.roll(np.roll(tD, di, axis=0), dj, axis=1)
            thisD = np.maximum(thisD, tD)

            # Deal with boundaries
            boundary = ~np.isnan(thisD)
            thisI = tidxs[boundary]
            thisJ = thisJ[boundary]
            thisD = thisD[boundary]

            I = np.concatenate((I, thisI.flatten()))
            J = np.concatenate((J, thisJ.flatten()))
            V = np.concatenate((V, thisD.flatten()))

    sparseDM = scipy.sparse.coo_matrix((V, (I, J)), shape=(idxs.size, idxs.size))

    return ripser.ripser(sparseDM, distance_matrix=True, maxdim=1)["dgms"]


if __name__ == "__main__":
    fname = sys.argv[1]
    if "x1x1_" in fname:
        reader = vtk.vtkXMLUnstructuredGridReader()
    elif "x1_" in fname:
        reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(fname)
    reader.Update()
    image_data = reader.GetOutput()
    if "x1x1_" in fname:
        dims = (-1, 1)
    elif "x1_" in fname:
        dims = image_data.GetDimensions()[0:2]
    dataset = dsa.WrapDataObject(image_data)
    array = dataset.PointData["ImageFile_Order"].reshape(dims)
    dgm = lower_star_img(array)
    print(dgm)

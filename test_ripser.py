import time

import numpy as np
import ripser
from scipy import sparse

import dionysus_gudhi_persistence


def lower_star_img(img):
    """
    Construct a lower star filtration on an image
    Parameters
    ----------
    img: ndarray (M, N)
        An array of single channel image data
    Returns
    -------
    I: ndarray (K, 2)
        A 0-dimensional persistence diagram corresponding to the sublevelset filtration
    """
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

    sparseDM = sparse.coo_matrix((V, (I, J)), shape=(idxs.size, idxs.size))

    print(sparseDM.todense())


def test():
    data = np.arange(0, 9).reshape((3, 3))
    print(data)
    lower_star_img(data)


def main(dataset, output):
    dims, vals, (edges, _, _) = dionysus_gudhi_persistence.read_simplicial_complex(
        dataset
    )
    edges = edges.reshape(-1, 2)

    start = time.time()

    I = np.zeros(dims[1], dtype=np.int32)
    J = np.zeros(dims[1], dtype=np.int32)
    V = np.zeros(dims[1], dtype=np.double)

    for i, e in enumerate(edges):
        I[i] = e[0]
        J[i] = e[1]
        V[i] = vals[dims[0] + i]

    sparseDM = sparse.coo_matrix((V, (I, J)), shape=(dims[0], dims[0]))

    print(f"Filled sparse distance matrix: {time.time() - start:.3f}s")
    start = time.time()

    diag = ripser.ripser(sparseDM, distance_matrix=True, maxdim=2)["dgms"]

    print(f"Computed persistence diagram: {time.time() - start:.3f}s")

    with open(output, "w") as dst:
        for i, pairs in enumerate(diag):
            for pair in pairs:
                dst.write(f"{i} {pair[0]} {pair[1]}\n")


if __name__ == "__main__":
    test()
    main("datasets/fuel_64x64x64_uint8_order_expl.tsc", "out.gudhi")

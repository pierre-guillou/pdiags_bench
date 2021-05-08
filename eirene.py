import numpy as np
from scipy import sparse

import dipha_explicit


def read_dipha_complex(fname):
    with open(fname, "rb") as src:
        if not dipha_explicit.check_type(src):
            raise TypeError

        ncells = int.from_bytes(src.read(8), "little", signed=True)
        print(f"Number of cells: {ncells}")
        dim = int.from_bytes(src.read(8), "little", signed=True)
        print(f"Global dataset dimension: {dim}")

        cell_dims = np.fromfile(src, dtype=np.int64, count=ncells)
        dims = np.array([np.sum(cell_dims == i) for i in range(dim + 1)])
        for i, v in enumerate(dims):
            print(f"  {v} cells of dimension {i}")
        values = np.fromfile(src, dtype=np.double, count=ncells)
        offsets = np.fromfile(src, dtype=np.int64, count=ncells + 1)
        psum_dims = np.cumsum(dims)
        nentries = offsets[-1]
        bmat = np.fromfile(src, dtype=np.int64, count=nentries)
        edges = bmat[offsets[psum_dims[0]] : offsets[psum_dims[1]]]
        triangles = bmat[offsets[psum_dims[1]] : offsets[psum_dims[2]]]
        tetras = bmat[offsets[psum_dims[2]] : offsets[psum_dims[3]]]
        return dims, values, (edges, triangles, tetras)


def main(dataset, output):
    dims, vals, (edges, triangles, tetras) = read_dipha_complex(dataset)
    edges = edges.reshape(-1, 2)
    triangles = triangles.reshape(-1, 3)
    tetras = tetras.reshape(-1, 4)

    n_entries = np.dot(dims[1:], np.arange(2, 5))

    I = np.zeros(n_entries, dtype=np.int32)
    J = np.zeros(n_entries, dtype=np.int32)
    V = np.ones(n_entries, dtype=np.int8)

    for i, e in enumerate(edges):
        o = 2 * i
        for k, v in enumerate(e):
            I[o + k] = v
            J[o + k] = i + dims[0]

    for i, t in enumerate(triangles):
        o = 3 * i + 2 * dims[1]
        for k, e in enumerate(t):
            I[o + k] = e
            J[o + k] = i + dims[0] + dims[1]

    for i, T in enumerate(tetras):
        o = 4 * i + 3 * dims[2] + 2 * dims[1]
        for k, t in enumerate(T):
            I[o + k] = t
            J[o + k] = i + dims[0] + dims[1] + dims[2]

    sparse_mat = sparse.csc_matrix((V, (I, J)))
    print(sparse_mat.shape)

    with open(output, "w") as dst:
        dims.tofile(dst, sep=",")  # ev
        dst.write("\n")

        vals.tofile(dst, sep=",")  # fv
        dst.write("\n")

        rv = sparse_mat.indices + 1  # Julia is 1 indexed
        rv.tofile(dst, sep=",")
        dst.write("\n")

        cp = sparse_mat.indptr + 1  # Julia is 1 indexed
        cp.tofile(dst, sep=",")
        dst.write("\n")


if __name__ == "__main__":
    main("datasets/fuel_64x64x64_uint8_order_expl.dipha", "eirene.csv")

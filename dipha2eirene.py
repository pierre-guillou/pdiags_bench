import argparse

import numpy as np
from scipy import sparse


def check_type(src):
    magic = int.from_bytes(src.read(8), "little", signed=True)
    if magic != 8067171840:
        print("Not a Dipha file")
        return False
    dtype = int.from_bytes(src.read(8), "little", signed=True)
    if dtype != 0:
        print("Not a Dipha Explicit Complex")
        return False
    mtype = int.from_bytes(src.read(8), "little", signed=True)
    if mtype != 0:
        print("Incorrect matrix type")
        return False

    return True


def read_dipha_complex(fname):
    with open(fname, "rb") as src:
        if not check_type(src):
            raise TypeError

        ncells = int.from_bytes(src.read(8), "little", signed=True)
        dim = int.from_bytes(src.read(8), "little", signed=True)
        cell_dims = np.fromfile(src, dtype=np.int64, count=ncells)
        dims = np.array([np.sum(cell_dims == i) for i in range(dim + 1)])
        values = np.fromfile(src, dtype=np.double, count=ncells)
        offsets = np.fromfile(src, dtype=np.int64, count=ncells + 1)
        psum_dims = np.cumsum(dims)
        nentries = offsets[-1]
        bmat = np.fromfile(src, dtype=np.int64, count=nentries)
        edges = bmat[offsets[psum_dims[0]] : offsets[psum_dims[1]]]
        triangles = bmat[offsets[psum_dims[1]] : offsets[psum_dims[2]]]
        tetras = bmat[offsets[psum_dims[2]] : offsets[psum_dims[3]]]
        return dims, values, (edges, triangles, tetras)


def generate_sparse_mat(dims, edges, triangles, tetras):
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

    return sparse.csc_matrix((V, (I, J)))


def generate_csv(sparse_mat, dims, vals, output_csv):
    with open(output_csv, "w") as dst:
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


def main(dataset, output_csv=""):
    if not output_csv:
        parts = dataset.split(".")
        parts[-1] = "csv"
        output_csv = ".".join(parts)

    dims, vals, (edges, triangles, tetras) = read_dipha_complex(dataset)
    edges = edges.reshape(-1, 2)
    triangles = triangles.reshape(-1, 3)
    tetras = tetras.reshape(-1, 4)

    sparse_mat = generate_sparse_mat(dims, edges, triangles, tetras)
    generate_csv(sparse_mat, dims, vals, output_csv)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Eirene.jl input CSV files from Dipha boundary matrices"
    )
    parser.add_argument("input", help="Path to the input Dipha file")
    parser.add_argument("output", help="Output Sparse Column CSV format")
    args = parser.parse_args()

    main(args.input, args.output)

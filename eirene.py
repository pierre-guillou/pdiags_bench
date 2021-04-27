import numpy as np

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
        dims = [np.sum(cell_dims == i) for i in range(dim + 1)]
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
    psum_dims = np.cumsum(dims)

    with open(output, "w") as dst:
        print(", ".join([str(dim) for dim in dims]), file=dst)  # ev
        print(", ".join([str(val) for val in vals]), file=dst)  # fv
        rowval = list()  # rv
        for e in edges:
            rowval.extend([v + 1 for v in e])
        for t in triangles:
            rowval.extend([e + 1 for e in t])
        for T in tetras:
            rowval.extend([t + 1 for t in T])
        print(", ".join([str(row) for row in rowval]), file=dst)
        colptr = np.concatenate(  # cp
            [
                np.arange(dims[0] + 1, psum_dims[1] + 1, 2),
                np.arange(psum_dims[1] + 1, psum_dims[2] + 1, 3),
                np.arange(psum_dims[2] + 1, psum_dims[3] + 1, 4),
            ]
        )
        colptr = np.append(colptr, 2 * dims[1] + 3 * dims[2] + 4 * dims[3])
        print(", ".join([str(col) for col in colptr]), file=dst)


if __name__ == "__main__":
    main("datasets/fuel_64x64x64_uint8_order_expl.dipha", "eirene.csv")

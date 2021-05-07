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
    psum_dims = np.cumsum(dims)

    with open(output, "w") as dst:
        dims.tofile(dst, sep=",")  # ev
        dst.write("\n")
        vals.tofile(dst, sep=",")  # fv
        dst.write("\n")

        rowval = np.zeros(np.dot(dims[1:], np.arange(2, 5)), dtype=np.int32)  # rv
        for i, e in enumerate(edges):
            rowval[2 * i + 0] = e[0] + 1
            rowval[2 * i + 1] = e[1] + 1
        for i, t in enumerate(triangles):
            j = 3 * i + 2 * dims[1]
            rowval[j + 0] = t[0] + 1
            rowval[j + 1] = t[1] + 1
            rowval[j + 2] = t[2] + 1
        for i, T in enumerate(tetras):
            j = 4 * i + 3 * dims[2] + 2 * dims[1]
            rowval[j + 0] = T[0] + 1
            rowval[j + 1] = T[1] + 1
            rowval[j + 2] = T[2] + 1
            rowval[j + 3] = T[3] + 1
        rowval.tofile(dst, sep=",")
        dst.write("\n")
        colptr = np.concatenate(  # cp
            [
                np.arange(dims[0] + 1, psum_dims[1] + 1, 2),
                np.arange(psum_dims[1] + 1, psum_dims[2] + 1, 3),
                np.arange(psum_dims[2] + 1, psum_dims[3] + 1, 4),
            ]
        )
        colptr = np.append(colptr, 2 * dims[1] + 3 * dims[2] + 4 * dims[3])
        colptr.tofile(dst, sep=",")
        dst.write("\n")


if __name__ == "__main__":
    main("datasets/fuel_64x64x64_uint8_order_expl.dipha", "eirene.csv")

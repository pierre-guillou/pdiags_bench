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

    def write_csv(dst, dim, val, facets):
        dst.write(f"{dim}, {val}, {', '.join([str(f + 1) for f in facets])}\n")

    with open(output, "w") as dst:
        for i in range(dims[0]):
            dst.write(f"0, {vals[i]}\n")
        for i, e in enumerate(edges):
            write_csv(dst, 1, vals[psum_dims[0] + i], e)
        for i, t in enumerate(triangles):
            write_csv(dst, 2, vals[psum_dims[1] + i], t)
        for i, T in enumerate(tetras):
            write_csv(dst, 3, vals[psum_dims[2] + i], T)


if __name__ == "__main__":
    main("datasets/fuel_64x64x64_uint8_order_expl.dipha", "eirene.csv")

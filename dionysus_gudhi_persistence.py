import enum
import time

import dionysus
import gudhi
import numpy as np


def read_simplicial_complex(dataset):
    start = time.time()

    with open(dataset, "rb") as src:
        magic = src.read(20)
        if magic != b"TTKSimplicialComplex":
            print("Not a TTK Simplicial Complex file")
            return None

        ncells = int.from_bytes(src.read(4), "little", signed=True)
        print(f"Number of cells: {ncells}")

        dim = int.from_bytes(src.read(4), "little", signed=True)
        print(f"Global dataset dimension: {dim}")

        dims = [0, 0, 0, 0]
        for i, _ in enumerate(dims):
            dims[i] = int.from_bytes(src.read(4), "little", signed=True)
        for i in range(dim + 1):
            print(f"  {dims[i]} cells of dimension {i}")

        values = np.fromfile(src, dtype=np.double, count=ncells)

        num_entries = int.from_bytes(src.read(4), "little", signed=True)
        print(f"Number of entries in boundary matrix: {num_entries}")

        edges = np.fromfile(src, dtype=np.int32, count=2 * dims[1])
        triangles = np.fromfile(src, dtype=np.int32, count=3 * dims[2])
        tetras = np.fromfile(src, dtype=np.int32, count=4 * dims[3])

    print(f"Read TTK Simplicial Complex file: {time.time() - start:.3f}s")
    return dims, values, (edges, triangles, tetras)


def compute_persistence_dionysus(dims, values, cpx):
    start = time.time()

    edges, triangles, tetras = cpx

    f = dionysus.Filtration()
    for i in range(dims[0]):
        f.append(dionysus.Simplex([i], values[i]))
    for i in range(dims[1]):
        o = 2 * i
        a = dims[0] + i
        f.append(dionysus.Simplex(edges[o : o + 2], values[a]))
    for i in range(dims[2]):
        o = 3 * i
        a = dims[0] + dims[1] + i
        f.append(dionysus.Simplex(triangles[o : o + 3], values[a]))
    for i in range(dims[3]):
        o = 4 * i
        a = dims[0] + dims[1] + dims[2] + i
        f.append(dionysus.Simplex(tetras[o : o + 4], values[a]))

    print(f"Filled filtration with Dionysus: {time.time() - start:.3f}s")
    start = time.time()

    f.sort()
    m = dionysus.homology_persistence(f)
    d = dionysus.init_diagrams(m, f)

    print(f"Computed persistence with Dionysus: {time.time() - start:.3f}s")

    return d


def write_diagram_dionysus(diag, output):
    with open(output, "w") as dst:
        for i, pair in enumerate(diag):
            for pt in pair:
                dst.write(f"{i} {pt.birth} {pt.death}\n")


def compute_persistence_gudhi(dims, values, cpx, output):
    start = time.time()

    edges, triangles, tetras = cpx

    st = gudhi.SimplexTree()
    for i in range(dims[0]):
        st.insert([i], filtration=values[i])
    for i in range(dims[1]):
        o = 2 * i
        a = dims[0] + i
        st.insert(edges[o : o + 2], filtration=values[a])
    for i in range(dims[2]):
        o = 3 * i
        a = dims[0] + dims[1] + i
        st.insert(triangles[o : o + 3], filtration=values[a])
    for i in range(dims[3]):
        o = 4 * i
        a = dims[0] + dims[1] + dims[2] + i
        st.insert(tetras[o : o + 4], filtration=values[a])

    print(f"Filled simplex tree with Gudhi: {time.time() - start:.3f}s")
    start = time.time()

    st.compute_persistence()

    print(f"Computed persistence with Gudhi: {time.time() - start:.3f}s")

    st.write_persistence_diagram(output)


class Backend(enum.Enum):
    DIONYSUS = 1
    GUDHI = 2


def main(dataset, output, backend=Backend.GUDHI):
    dims, vals, cpx = read_simplicial_complex(dataset)
    if backend == Backend.DIONYSUS:
        diag = compute_persistence_dionysus(dims, vals, cpx)
        write_diagram_dionysus(diag, output)
    elif backend == Backend.GUDHI:
        compute_persistence_gudhi(dims, vals, cpx, output)


if __name__ == "__main__":
    main("datasets/fuel_64x64x64_uint8_order_expl.tsc", "out.gudhi")

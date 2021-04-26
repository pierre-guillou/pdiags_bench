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


class Dionysus_Filtration:
    def __init__(self):
        self.f = dionysus.Filtration()
        self.diag = None
        print("Use the Dionysus2 backend")

    def add(self, verts, val):
        self.f.append(dionysus.Simplex(verts, val))

    def compute_pers(self):
        self.f.sort()
        m = dionysus.homology_persistence(self.f)
        self.diag = dionysus.init_diagrams(m, self.f)

    def write_diag(self, output):
        with open(output, "w") as dst:
            for i, pair in enumerate(self.diag):
                for pt in pair:
                    dst.write(f"{i} {pt.birth} {pt.death}\n")


class Gudhi_SimplexTree:
    def __init__(self):
        self.st = gudhi.SimplexTree()
        print("Use the Gudhi Simplex Tree backend")

    def add(self, verts, val):
        self.st.insert(verts, filtration=val)

    def compute_pers(self):
        self.st.compute_persistence()

    def write_diag(self, output):
        self.st.write_persistence_diagram(output)


def compute_persistence(wrapper, dims, values, cpx, output):
    start = time.time()

    edges, triangles, tetras = cpx

    for i in range(dims[0]):
        wrapper.add([i], values[i])
    for i in range(dims[1]):
        o = 2 * i
        a = dims[0] + i
        wrapper.add(edges[o : o + 2], values[a])
    for i in range(dims[2]):
        o = 3 * i
        a = dims[0] + dims[1] + i
        wrapper.add(triangles[o : o + 3], values[a])
    for i in range(dims[3]):
        o = 4 * i
        a = dims[0] + dims[1] + dims[2] + i
        wrapper.add(tetras[o : o + 4], values[a])

    print(f"Filled filtration/simplex tree: {time.time() - start:.3f}s")
    start = time.time()

    wrapper.compute_pers()

    print(f"Computed persistence: {time.time() - start:.3f}s")

    wrapper.write_diag(output)


def main(dataset, output, backend="Gudhi", simplicial=True):
    if simplicial:
        dims, vals, cpx = read_simplicial_complex(dataset)
        dispatch = {
            "Dionysus": Dionysus_Filtration,
            "Gudhi": Gudhi_SimplexTree,
        }
        compute_persistence(dispatch[backend](), dims, vals, cpx, output)

    elif backend == "Gudhi":
        print("Use the Gudhi Cubical Complex backend")

        start = time.time()
        cpx = gudhi.CubicalComplex(perseus_file=dataset)
        print(f"Loaded Perseus file: {time.time() - start:.3f}s")

        print(f"Number of simplices: {cpx.num_simplices()}")
        print(f"Global dimension: {cpx.dimension()}")

        start = time.time()
        diag = cpx.persistence()
        print(f"Computed persistence: {time.time() - start:.3f}s")

        with open(output, "w") as dst:
            for dim, (birth, death) in diag:
                dst.write(f"{dim} {birth} {death}\n")

    else:
        print("Cannot use Dionysus with cubical complexes")


if __name__ == "__main__":
    main("datasets/fuel_64x64x64_uint8_order_expl.tsc", "out.gudhi")

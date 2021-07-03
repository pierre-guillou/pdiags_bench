import argparse
import math
import re
import subprocess
import time
import sys

import dionysus
import numpy as np


def read_simplicial_complex(dataset):
    start = time.time()

    with open(dataset, "rb") as src:
        magic = src.read(20)
        if magic != b"TTKSimplicialComplex":
            print("Not a TTK Simplicial Complex file")
            raise TypeError

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


class Ripser_SparseDM:
    def __init__(self):
        self.dist_mat = None
        self.diag = None
        print("Using the Ripser.py backend")

    def fill_dist_mat(self, dims, vals, edges):
        edges = edges.reshape(-1, 2)
        I = np.zeros(dims[0] + 2 * dims[1], dtype=np.int32)
        J = np.zeros(dims[0] + 2 * dims[1], dtype=np.int32)
        V = np.zeros(dims[0] + 2 * dims[1], dtype=np.double)

        for i in range(dims[0]):
            I[i] = i
            J[i] = i
            V[i] = vals[i]

        for i, e in enumerate(edges):
            o = dims[0] + 2 * i
            I[o + 0] = e[0]
            J[o + 0] = e[1]
            I[o + 1] = e[1]
            J[o + 1] = e[0]
            V[o + 0] = vals[dims[0] + i]
            V[o + 1] = vals[dims[0] + i]

        self.dist_mat = "\n".join([f"{i} {j} {v}" for i, j, v in zip(I, J, V)])

    def compute_pers(self):
        proc = subprocess.run(
            ["ripser/ripser", "--format", "sparse"],
            check=True,
            input=self.dist_mat.encode(),
            capture_output=True,
        )
        self.diag = proc.stdout.decode()

    def write_diag(self, output):
        dim = 0
        pairs = list()
        for line in self.diag.split("\n"):
            if line == " [0, )":
                pairs.append([0, 0, math.inf])
            dim_pat = r"persistence intervals in dim (\d+):"
            try:
                dim = re.search(dim_pat, line).group(1)
            except AttributeError:
                pass
            pair_pat = r"\[(\d+),(\d+)\)"
            try:
                birth, death = re.search(pair_pat, line).groups()
                pairs.append([dim, birth, death])
            except AttributeError:
                pass

        with open(output, "w") as dst:
            for dim, birth, death in pairs:
                if int(dim) == 0 and float(birth) == 0 and float(death) != math.inf:
                    # filter out min-sad pairs beginning from 0
                    continue
                dst.write(f"{dim} {birth} {death}\n")


class Dionysus_Filtration:
    def __init__(self):
        self.f = dionysus.Filtration()
        self.diag = None
        print("Using the Dionysus2 backend")

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
        import gudhi

        self.st = gudhi.SimplexTree()
        self.pairs = list()
        print("Using the Gudhi Simplex Tree backend")

    def add(self, verts, val):
        self.st.insert(verts, filtration=val)

    def compute_pers(self):
        self.pairs = self.st.persistence()

    def write_diag(self, output):
        with open(output, "w") as dst:
            for dim, (birth, death) in self.pairs:
                dst.write(f"{dim} {birth} {death}\n")


def compute_persistence(wrapper, dims, values, cpx, output):
    start = time.time()

    edges, triangles, tetras = cpx

    if isinstance(wrapper, Ripser_SparseDM):
        wrapper.fill_dist_mat(dims, values, edges)
    else:
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

    prec = round(time.time() - start, 3)
    print(f"Filled filtration/simplex tree/distance matrix: {prec}s")
    start = time.time()

    wrapper.compute_pers()

    pers = round(time.time() - start, 3)
    print(f"Computed persistence: {pers}s")

    wrapper.write_diag(output)

    return (prec, pers)


def run(dataset, output, backend="Gudhi", simplicial=True):
    if simplicial:
        dims, vals, cpx = read_simplicial_complex(dataset)
        dispatch = {
            "Dionysus": Dionysus_Filtration,
            "Gudhi": Gudhi_SimplexTree,
            "Ripser": Ripser_SparseDM,
        }
        return compute_persistence(dispatch[backend](), dims, vals, cpx, output)

    if backend == "Gudhi":
        print("Use the Gudhi Cubical Complex backend")
        import gudhi

        start = time.time()
        cpx = gudhi.CubicalComplex(perseus_file=dataset)
        print(f"Loaded Perseus file: {time.time() - start:.3f}s")

        print(f"Number of simplices: {cpx.num_simplices()}")
        print(f"Global dimension: {cpx.dimension()}")

        start = time.time()
        diag = cpx.persistence()
        pers = round(time.time() - start, 3)
        print(f"Computed persistence: {pers}s")

        with open(output, "w") as dst:
            for dim, (birth, death) in diag:
                dst.write(f"{dim} {birth} {death}\n")

        return (0.0, pers)

    print("Cannot use Dionysus with cubical complexes")
    return (0.0, 0.0)


def main():
    parser = argparse.ArgumentParser(
        description="Apply Gudhi, Dionysus2 or Ripser on the given dataset"
    )

    parser.add_argument(
        "-i",
        type=str,
        help="Path to input dataset",
        default="datasets/fuel_64x64x64_uint8_order_expl.tsc",
        dest="input_dataset",
    )
    parser.add_argument(
        "-o",
        type=str,
        help="Output diagram file name",
        default="out.gudhi",
        dest="output_diagram",
    )
    parser.add_argument(
        "-p",
        "--gudhi_path",
        type=str,
        help="Path to Gudhi Python module",
        default="build_gudhi/src/python",
    )
    parser.add_argument(
        "-b", choices=["gudhi", "dionysus", "ripser"], default="gudhi", dest="backend"
    )
    args = parser.parse_args()

    ext = args.input_dataset.split(".")[-1]

    if ext not in ["tsc", "pers"]:
        print("Input dataset not supported")

    if ext == "pers" and args.backend != "gudhi":
        print("Perseus Cubical Complex files can only be processed by Gudhi")
        return

    if ext == "pers" and "expl" in args.input_dataset:
        print("Perseus Simplicial Complex files not supported")
        return

    # prepend path to Gudhi Python package to PYTHONPATH
    sys.path = [args.gudhi_path] + sys.path

    run(
        args.input_dataset,
        args.output_diagram,
        backend=args.backend.capitalize(),
        simplicial="expl" in args.input_dataset,
    )


if __name__ == "__main__":
    main()

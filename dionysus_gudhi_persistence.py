import argparse
import os
import re
import subprocess
import sys
import time

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
        self.maxdim = 0
        print("Using the Ripser backend")

    def fill_dist_mat(self, dims, vals, edges):
        edges = edges.reshape(-1, 2)
        I = np.zeros(dims[0] + dims[1], dtype=np.int32)
        J = np.zeros(dims[0] + dims[1], dtype=np.int32)
        V = np.zeros(dims[0] + dims[1], dtype=np.double)

        if dims[2] != 0:
            self.maxdim = 1
        if dims[3] != 0:
            self.maxdim = 2

        for i in range(dims[0]):
            I[i] = i
            J[i] = i
            V[i] = vals[i]

        for i, e in enumerate(edges):
            o = dims[0] + i
            I[o] = e[0]
            J[o] = e[1]
            V[o] = vals[dims[0] + i]

        with open("dist_mat", "w") as dst:
            for i, j, v in zip(I, J, V):
                dst.write(f"{i} {j} {v}\n")

    def compute_pers(self):
        cmd = (
            ["backends_src/ripser/ripser"]
            + ["--format", "sparse"]
            + ["--dim", "2"]
            + ["dist_mat"]
        )
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        ) as proc:
            self.diag = [[], [], []]
            if proc.returncode != 0:
                print(proc.stderr.read())
                raise subprocess.CalledProcessError(proc.returncode, cmd)
            for line in proc.stdout.readlines():
                if "intervals" in line:
                    dim = int(line.strip()[-2])
                line = line.strip()
                m = re.search(r"\[(\d+|\d+.\d+),(\d+|\d+.\d+)?\)", line)
                if m is not None:
                    self.diag[dim].append((m.groups()[0], m.groups()[1]))
            os.remove("dist_mat")

    def write_diag(self, output):
        n_pairs = 0
        for pairs in self.diag:
            n_pairs += len(pairs)
        if n_pairs == 0:
            return
        with open(output, "w") as dst:
            for dim, pairs in enumerate(self.diag):
                for birth, death in pairs:
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
        self.pairs = []
        print("Using the Gudhi Simplex Tree backend")

    def add(self, verts, val):
        self.st.insert(verts, filtration=val)

    def compute_pers(self):
        self.pairs = self.st.persistence()

    def write_diag(self, output):
        with open(output, "w") as dst:
            for dim, (birth, death) in self.pairs:
                dst.write(f"{dim} {birth:.3f} {death:.3f}\n")


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
                dst.write(f"{dim} {birth:.3f} {death:.3f}\n")

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
        default="build_dirs/gudhi/src/python",
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
        simplicial="expl" in args.input_dataset or "tsc" in args.input_dataset,
    )


if __name__ == "__main__":
    main()

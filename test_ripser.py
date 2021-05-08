import math
import re
import subprocess

import numpy as np

import dionysus_gudhi_persistence


def parse_write_pairs(ripser_pairs, output):
    dim = 0
    pairs = list()
    for line in ripser_pairs.split("\n"):
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


def main(dataset, output):
    dims, vals, (edges, _, _) = dionysus_gudhi_persistence.read_simplicial_complex(
        dataset
    )
    edges = edges.reshape(-1, 2)

    I = np.zeros(dims[1], dtype=np.int32)
    J = np.zeros(dims[1], dtype=np.int32)
    V = np.zeros(dims[1], dtype=np.double)

    for i, e in enumerate(edges):
        I[i] = e[0]
        J[i] = e[1]
        V[i] = vals[dims[0] + i]

    sparse_mat = "\n".join([f"{i} {j} {v}" for i, j, v in zip(I, J, V)]).encode()

    proc = subprocess.run(
        ["ripser/ripser", "--format", "sparse", "--dim", "2"],
        check=True,
        input=sparse_mat,
        capture_output=True,
    )
    parse_write_pairs(proc.stdout.decode(), output)


if __name__ == "__main__":
    main("datasets/fuel_64x64x64_uint8_order_expl.tsc", "out.gudhi")

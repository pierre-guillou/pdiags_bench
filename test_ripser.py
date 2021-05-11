import argparse
import math
import re
import subprocess

import numpy as np


def load_raw(input_raw):
    extension = input_raw.split(".")[-1]
    if extension != "raw":
        print("Need a .raw file")
        raise TypeError

    extent, dtype = input_raw.split(".")[0].split("_")[-2:]
    extent = [int(dim) for dim in extent.split("x")]

    dtype_np = {
        "uint8": np.uint8,
        "int16": np.int16,
        "uint16": np.uint16,
        "float32": np.float32,
        "float64": np.float64,
    }
    dtype = dtype_np[dtype]

    with open(input_raw) as src:
        data = np.fromfile(src, dtype=dtype)
        return data.reshape(extent)


def compute_persistence(sparse_triplets):
    proc = subprocess.Popen(
        ["ripser/ripser", "--format", "sparse", "--dim", "2"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    out, _ = proc.communicate(sparse_triplets)
    return out


def build_sparse_triplets(data):
    triplets = list()

    with np.nditer(data, flags=["multi_index"]) as it:
        for v in it:
            for d in range(data.ndim):
                for s in [-1, 1]:
                    coords = list(it.multi_index)
                    s = coords[d] + s
                    if s < 0 or s >= data.shape[d]:
                        continue
                    coords[d] = s
                    triplets.append(
                        [
                            np.ravel_multi_index(it.multi_index, data.shape),
                            np.ravel_multi_index(coords, data.shape),
                            max(data[tuple(coords)], v),
                        ]
                    )

    return "\n".join([f"{i} {j} {v}" for i, j, v in triplets])


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


def main(input_raw, output_diagram):
    data = load_raw(input_raw)
    sparse_triplets = build_sparse_triplets(data)
    ripser_pairs = compute_persistence(sparse_triplets)
    parse_write_pairs(ripser_pairs, output_diagram)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wrapper around Ripser C++")
    parser.add_argument("input_raw", help="Input raw file from OpenSciVis datasets")
    parser.add_argument(
        "-o",
        "--output_diagram",
        help="Output diagram in Gudhi format",
        default="out.gudhi",
    )
    args = parser.parse_args()

    main(args.input_raw, args.output_diagram)

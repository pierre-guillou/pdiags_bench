import argparse
import os
import subprocess
import time


def main(input_dataset, output_diagram, phat_exec):
    # call PHAT on input dataset
    phat_diag = "diagram.phat"
    subprocess.check_call(
        [phat_exec, "--verbose", "--ascii", "--spectral_sequence"]
        + [input_dataset, phat_diag]
    )

    start = time.time()

    # read PHAT persistence_pairs binary format file
    with open(phat_diag) as src:
        n_pairs = int(src.readline())
        pairs = []
        for i, line in enumerate(src):
            pairs.append([int(a) for a in line.split(" ")])
            if i == n_pairs:
                break
    os.remove(phat_diag)

    # get offset, dim from input_dataset
    with open(input_dataset) as src:
        n_verts = -1
        offsets = []
        dims = []
        for i, line in enumerate(src):
            if line.startswith("0"):
                n_verts += 1
            offsets.append(n_verts)
            dims.append(int(line.strip().split()[0]))

    # write pairs in Gudhi format
    with open(output_diagram, "w") as dst:
        for birth, death in pairs:
            ob = offsets[birth]
            od = offsets[death]
            dim = dims[birth]
            if ob != od:
                dst.write(f"{dim} {ob} {od}\n")

    print(f"Converted PHAT pairs to Gudhi format (took {time.time() - start:.3f}s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply PHAT on the given dataset")

    parser.add_argument(
        "input_dataset",
        type=str,
        help="Path to input dataset",
    )
    parser.add_argument(
        "-o",
        "--output_diagram",
        type=str,
        help="Output diagram file name",
        default="out.gudhi",
    )
    parser.add_argument(
        "-p",
        "--phat_exec",
        type=str,
        help="Path to PHAT executable",
        default="build_phat/phat",
    )

    args = parser.parse_args()
    main(args.input_dataset, args.output_diagram, args.phat_exec)

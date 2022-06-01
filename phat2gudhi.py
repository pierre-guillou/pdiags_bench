import argparse
import multiprocessing
import os
import re
import subprocess
import time


def main(input_dataset, output_diagram, phat_exec, thread_number):
    # call PHAT on input dataset
    phat_diag = "diagram.phat"

    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = str(thread_number)

    subprocess.check_call(
        [phat_exec, "--verbose", "--ascii", "--spectral_sequence"]
        + [input_dataset, phat_diag],
        env=env,
    )

    start = time.time()

    patt = re.compile(r".*_(\d+)x(\d+)x(\d+)_.*")
    dims = [int(a) for a in re.match(patt, input_dataset).groups()]
    max_death = dims[0] * dims[1] * dims[2] - 1

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
                # fix death of global min-max pair
                if dim == 0 and ob == 0 and od == 1:
                    od = max_death
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
        default="build_dirs/phat/phat",
    )
    parser.add_argument(
        "-t",
        "--thread_number",
        type=int,
        help="Number of threads",
        default=multiprocessing.cpu_count(),
    )

    args = parser.parse_args()
    main(args.input_dataset, args.output_diagram, args.phat_exec, args.thread_number)

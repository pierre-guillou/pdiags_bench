#!/usr/bin/env python3

import argparse
import glob
import json
import os
import re
import subprocess
import time

import convert_datasets

URL = "https://klacansky.com/open-scivis-datasets/data_sets.json"
SIZE_LIMIT_MB = 80


def create_dir(dirname):
    try:
        os.mkdir(dirname)
    except FileExistsError:
        pass


def prepare_datasets(_, size_limit=SIZE_LIMIT_MB, download=False):
    create_dir("datasets")
    for dataset in sorted(glob.glob("*.raw")):
        convert_datasets.main(dataset.split("/")[-1], "datasets")


def dipha_print_pairs(dipha_diag):
    with open(dipha_diag, "rb") as src:
        magic = int.from_bytes(src.read(8), "little", signed=True)
        if magic != 8067171840:
            print("Not a Dipha file")
            return
        dtype = int.from_bytes(src.read(8), "little", signed=True)
        if dtype != 2:
            print("Not a Dipha Persistence Diagram")
            return
        npairs = int.from_bytes(src.read(8), "little", signed=True)
        if npairs < 0:
            print("Negative number of persistence pairs")
            return
        nptypes = dict()
        for i in range(npairs):
            ptype = int.from_bytes(src.read(8), "little", signed=True)
            src.read(8)  # birth
            src.read(8)  # death
            nptypes[ptype] = nptypes.get(ptype, 0) + 1
        nptypes[0] = nptypes.get(0, 0) + nptypes.get(-1, 0)
        del nptypes[-1]
        print(" #Min-Saddle pairs:", nptypes.get(0, 0))
        print(" #Saddle-Saddle pairs:", nptypes.get(1, 0))
        print(" #Saddle-Max pairs:", nptypes.get(2, 0))
        print(" #Total:", sum(nptypes.values()))
        print(" #Minima:", nptypes.get(0, 0))
        print(" #1-Saddles:", nptypes.get(1, 0) + nptypes.get(0, 0))
        print(" #2-Saddles:", nptypes.get(1, 0) + nptypes.get(2, 0))
        print(" #Maxima:", nptypes.get(2, 0))


def escape_ansi_chars(txt):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", txt)


def ttk_print_pairs(ttk_output):
    ttk_output = escape_ansi_chars(ttk_output.decode())
    patterns = [
        "Min-saddle pairs",
        "Saddle-saddle pairs",
        "Saddle-max pairs",
        "Minima",
        "1-saddles",
        "2-saddles",
        "Maxima",
    ]
    for pat in patterns:
        pat_re = fr"\[DiscreteGradient\].*#{pat}.*:.(\d+)"
        res = re.search(pat_re, ttk_output, re.MULTILINE).group(1)
        print(f" #{pat}:", res)


def dataset_name(dsfile):
    """File name without extension and without directory"""
    return dsfile.split(".")[0].split("/")[-1]


def compute_ttk(fname, exe, times, dipha_offload=False, one_thread=False):
    dataset = dataset_name(fname)
    if dipha_offload:
        print("Processing " + dataset + " with TTK offloading to Dipha...")
    else:
        print("Processing " + dataset + " with TTK...")
    outp = f"diagrams/{dataset}.vtu"
    cmd = [exe, "-i", fname, "-d", "4"]
    if one_thread:
        cmd.extend(["-t", "1"])
    key = "ttk"
    if dipha_offload:
        cmd.append("-wd")
        key = "ttk-dipha"
    proc = subprocess.run(cmd, capture_output=True)

    def ttk_compute_time(ttk_output):
        ttk_output = escape_ansi_chars(ttk_output.decode())
        time_re = r"\[PersistenceDiagram\] Complete.*\[(\d+\.\d+|\d+)s"
        return float(re.search(time_re, ttk_output, re.MULTILINE).group(1))

    def ttk_overhead_time(ttk_output):
        ttk_output = escape_ansi_chars(ttk_output.decode())
        time_re = (
            r"\[DiscreteGradient\] Wrote Dipha explicit complex.*\[(\d+\.\d+|\d+)s"
        )
        return float(re.search(time_re, ttk_output, re.MULTILINE).group(1))

    times[dataset][key] = ttk_compute_time(proc.stdout)
    if dipha_offload:
        times[dataset][key] -= ttk_overhead_time(proc.stdout)
        dipha_print_pairs("/tmp/output.dipha")
    else:
        ttk_print_pairs(proc.stdout)
    os.rename("output_port_0.vtu", outp)


def compute_dipha(fname, exe, times, one_thread=False):
    dataset = dataset_name(fname)
    print("Processing " + dataset + " with dipha...")
    outp = f"diagrams/{dataset}.dipha"
    if one_thread:
        cmd = [
            exe,
            "--benchmark",
            fname,
            outp,
        ]
    else:
        cmd = [
            "mpirun",
            "--use-hwthread-cpus",
            exe,
            "--benchmark",
            fname,
            outp,
        ]
    start_time = time.time()
    proc = subprocess.run(cmd, capture_output=True)
    dipha_exec_time = time.time() - start_time

    def dipha_compute_time(dipha_output, dipha_exec_time):
        dipha_output = dipha_output.decode()
        read_re = r"^\s+(\d+\.\d+|\d+).*complex.load_binary"
        write_re = r"^\s+(\d+\.\d+|\d+).*save_persistence_diagram"
        patterns = [read_re, write_re]
        overhead = [
            float(re.search(pat, dipha_output, re.MULTILINE).group(1))
            for pat in patterns
        ]
        return round(dipha_exec_time - sum(overhead), 3)

    times[dataset]["dipha"] = dipha_compute_time(proc.stdout, dipha_exec_time)
    dipha_print_pairs(outp)


def compute_cubrips(fname, exe, times):
    dataset = dataset_name(fname)
    if "float" in dataset:
        # skip large datasets
        return
    print("Processing " + dataset + " with CubicalRipser...")
    outp = f"diagrams/{dataset}.cr"
    cmd = [exe, fname, "--output", outp]
    try:
        start_time = time.time()
        subprocess.check_call(cmd)
        times[dataset]["CubicalRipser"] = time.time() - start_time
    except subprocess.CalledProcessError:
        print(dataset + " is too large for CubicalRipser")


def compute_gudhi(fname, exe, times):
    dataset = dataset_name(fname)
    print("Processing " + dataset + " with Gudhi...")
    outp = f"diagrams/{dataset}.gudhi"
    cmd = [exe, fname]
    start_time = time.time()
    subprocess.check_call(cmd)
    times[dataset]["gudhi"] = time.time() - start_time
    os.rename(fname + "_persistence", outp)


def compute_diagrams(_, all_softs=False):
    exes = {
        "ttk": "ttkPersistenceDiagramCmd",
        "dipha": "build_dipha/dipha",
        "gudhi": (
            "build_gudhi/src/Bitmap_cubical_complex"
            "/utilities/cubical_complex_persistence"
        ),
        "CubicalRipser": "CubicalRipser/CR3",
    }

    for exe in list(exes.values())[1:]:
        if not os.path.isfile(exe):
            print(exe + " not found")
            all_softs = False

    # output diagrams directory
    create_dir("diagrams")

    # store computation times
    times = dict()

    for fname in sorted(glob.glob("datasets/*")):
        # initialize compute times table
        times[dataset_name(fname)] = dict()

    one_thread = False

    for fname in sorted(glob.glob("datasets/*")):
        ext = fname.split(".")[-1]
        if ext == "vtu" or ext == "vti":
            compute_ttk(fname, exes["ttk"], times, False, one_thread)
            compute_ttk(fname, exes["ttk"], times, True, one_thread)
        elif ext == "dipha":
            compute_dipha(fname, exes["dipha"], times, one_thread)
        elif all_softs and ext == "dipha":
            compute_cubrips(fname, exes["CubicalRipser"], times)
        elif all_softs and ext == "pers":
            compute_gudhi(fname, exes["gudhi"], times)

    with open("results", "w") as dst:
        dst.write(json.dumps(times))
    return times


def compute_distances(_, method="auction"):
    # list of datasets that have at least one persistence diagram
    datasets = sorted(set(f.split(".")[0] for f in glob.glob("diagrams/*")))

    float_re = r"(\d+\.\d+|\d+)"
    auct_patt = re.compile(
        rf"(?:Min-saddle|Saddle-saddle|Saddle-max) cost\s+:\s+{float_re}"
    )
    btnk_patt = re.compile(rf"diag(?:Max|Min|Sad)\({float_re}\)")
    dists = dict()

    for ds in datasets:
        ttk_diag = ds + ".vtu"
        dipha_diag = ds + ".dipha"
        empty_diag = "empty.vtu"

        if os.path.isfile(ttk_diag) and os.path.isfile(dipha_diag):
            cmd = ["python", "ttk_distance.py", method, dipha_diag, ttk_diag]
            print(f"Computing distance between TTK and Dipha for {ds}")
            proc0 = subprocess.run(cmd, capture_output=True)
            cmd = ["python", "ttk_distance.py", method, dipha_diag, empty_diag]
            print(f"Computing Dipha distance to empty diagram for {ds}")
            proc1 = subprocess.run(cmd, capture_output=True)

            # match distance figures
            pattern = auct_patt if method == "auction" else btnk_patt
            matches0 = re.findall(pattern, str(proc0.stdout))
            matches1 = re.findall(pattern, str(proc1.stdout))

            # parse string to float
            matches0 = [float(m) for m in matches0]
            matches1 = [float(m) for m in matches1]

            pairTypes = ["min-sad", "sad-sad", "sad-max"]
            dists[ds] = {
                "ttk-dipha": dict(zip(pairTypes, matches0)),
                "empty-dipha": dict(zip(pairTypes, matches1)),
            }

    # clean pipeline sink
    os.remove("dist.vtu")

    with open("distances", "w") as dst:
        dst.write(json.dumps(dists))
    return dists


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Compute Persistence Diagrams with TTK, Dipha, Gudhi and "
            "CubicalRipser on a selection of OpenSciVis datasets"
        )
    )
    subparsers = parser.add_subparsers()

    prep_datasets = subparsers.add_parser("prepare_datasets")
    prep_datasets.set_defaults(func=prepare_datasets)

    get_diags = subparsers.add_parser("compute_diagrams")
    get_diags.set_defaults(func=compute_diagrams)

    get_dists = subparsers.add_parser("compute_distances")
    get_dists.set_defaults(func=compute_distances)

    cli_args = parser.parse_args()

    # force use of subcommand, display help without one
    if "func" in cli_args.__dict__:
        cli_args.func(cli_args)
    else:
        parser.parse_args(["--help"])


if __name__ == "__main__":
    main()

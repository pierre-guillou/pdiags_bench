#!/usr/bin/env python3

import argparse
import glob
import json
import multiprocessing
import os
import re
import subprocess
import time

import compare_diags
import convert_datasets


def create_dir(dirname):
    try:
        os.mkdir(dirname)
    except FileExistsError:
        pass


def prepare_datasets(_):
    create_dir("datasets")
    for dataset in sorted(glob.glob("raws/*.raw")):
        # reduce RAM usage by isolating datasets manipulation in
        # separate processes
        p = multiprocessing.Process(
            target=convert_datasets.main, args=(dataset, "datasets")
        )
        p.start()
        p.join()


def ttk_dipha_print_pairs(diag):
    pairs = compare_diags.read_diag(diag)
    print(f" #Min-saddle pairs: {len(pairs[0])}")
    print(f" #Saddle-saddle pairs: {len(pairs[1])}")
    print(f" #Saddle-max pairs: {len(pairs[2])}")
    print(f" Total: {sum(map(len, pairs))}")
    return {
        "#Min-saddle": len(pairs[0]),
        "#Saddle-saddle": len(pairs[1]),
        "#Saddle-max": len(pairs[2]),
    }


def escape_ansi_chars(txt):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", txt)


def dataset_name(dsfile):
    """File name without extension and without directory"""
    return dsfile.split(".")[0].split("/")[-1]


TIMEOUT_S = 1800  # 30 min


def compute_ttk(
    fname, exe, times, dipha_offload=False, hybrid_pp=False, one_thread=False
):
    dataset = dataset_name(fname)
    if dipha_offload:
        if hybrid_pp:
            print("Processing " + dataset + " with TTK (hybrid++ mode)...")
        else:
            print("Processing " + dataset + " with TTK (hybrid mode)...")
    else:
        print("Processing " + dataset + " with TTK...")
    outp = f"diagrams/{dataset}.vtu"
    cmd = [exe, "-i", fname, "-d", "4"]
    if one_thread:
        cmd.extend(["-t", "1"])
    key = "ttk"
    if dipha_offload:
        cmd.append("-wd")
        key = "ttk-hybrid"
        if hybrid_pp:
            cmd.append("-dpp")
            key = "ttk-hybrid++"

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

    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT_S)
        times[dataset][key] = ttk_compute_time(proc.stdout)
        os.rename("output_port_0.vtu", outp)
        ttk_dipha_print_pairs(outp)
    except subprocess.TimeoutExpired:
        print("Timeout reached, computation aborted")


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
    proc = subprocess.run(cmd, capture_output=True)  # no timeout here?
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

    ret = ttk_dipha_print_pairs(outp)
    times[dataset] |= ret
    times[dataset]["dipha"] = dipha_compute_time(proc.stdout, dipha_exec_time)


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
        subprocess.check_call(cmd, timeout=TIMEOUT_S)
        times[dataset]["CubicalRipser"] = round(time.time() - start_time, 3)
        ttk_dipha_print_pairs(outp)
    except subprocess.CalledProcessError:
        print(dataset + " is too large for CubicalRipser")
    except subprocess.TimeoutExpired:
        print("Timeout reached, computation aborted")


def compute_gudhi(fname, exe, times):
    dataset = dataset_name(fname)
    print("Processing " + dataset + " with Gudhi...")
    outp = f"diagrams/{dataset}.gudhi"
    cmd = [exe, fname]
    try:
        start_time = time.time()
        subprocess.check_call(cmd, timeout=TIMEOUT_S)
        times[dataset]["gudhi"] = round(time.time() - start_time, 3)
        os.rename(fname.split("/")[-1] + "_persistence", outp)
        ttk_dipha_print_pairs(outp)
    except subprocess.TimeoutExpired:
        print("Timeout reached, computation aborted")


def compute_diagrams(_, all_softs=True):
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

    one_thread = False

    for fname in sorted(glob.glob("datasets/*")):
        # initialize compute times table
        times[dataset_name(fname)] = {
            "#Threads": 1
            if one_thread or "impl" in fname
            else multiprocessing.cpu_count()
        }
        times[dataset_name(fname)]["#Vertices"] = "x".join(
            [str(convert_datasets.RESAMPL)] * 3
        )

    for fname in sorted(glob.glob("datasets/*")):
        ext = fname.split(".")[-1]
        if ext == "vtu" or ext == "vti":
            # our algo
            compute_ttk(
                fname,
                exes["ttk"],
                times,
                dipha_offload=False,
                hybrid_pp=False,
                one_thread=one_thread,
            )
            # ttk-hybrid: offload Morse-Smale complex to Dipha
            compute_ttk(
                fname,
                exes["ttk"],
                times,
                dipha_offload=True,
                hybrid_pp=False,
                one_thread=one_thread,
            )
            # ttk-hybrid++: offload saddle connectors to Dipha
            compute_ttk(
                fname,
                exes["ttk"],
                times,
                dipha_offload=True,
                hybrid_pp=True,
                one_thread=one_thread,
            )
        elif ext == "dipha" and "expl" in fname:
            compute_dipha(fname, exes["dipha"], times, one_thread)
        elif all_softs and ext == "dipha" and "impl" in fname:
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

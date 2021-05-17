#!/usr/bin/env python3

import argparse
import glob
import json
import multiprocessing
import os
import re
import subprocess

import compare_diags
import convert_datasets
import download_datasets
import pers2gudhi


def create_dir(dirname):
    try:
        os.mkdir(dirname)
    except FileExistsError:
        pass


def prepare_datasets(args):
    if args.download:
        download_datasets.main(args.max_dataset_size)

    create_dir("datasets")
    for dataset in sorted(glob.glob("raws/*.raw")):
        # reduce RAM usage by isolating datasets manipulation in
        # separate processes
        p = multiprocessing.Process(
            target=convert_datasets.main,
            args=(dataset, "datasets", args.max_resample_size),
        )
        p.start()
        p.join()


def get_pairs_number(diag):
    pairs = compare_diags.read_diag(diag)
    return {
        "#Min-saddle": len(pairs[0]),
        "#Saddle-saddle": len(pairs[1]),
        "#Saddle-max": len(pairs[2]),
        "#Total pairs": sum([len(p) for p in pairs]),
    }


def escape_ansi_chars(txt):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", txt)


def dataset_name(dsfile):
    """File name without extension and without directory"""
    return dsfile.split(".")[0].split("/")[-1]


TIMEOUT_S = 1800  # 30 min
RES_MEAS = [
    "python",
    "subprocess_wrapper.py",
    "--",
    "/usr/bin/timeout",
    "--preserve-status",
    str(TIMEOUT_S),
]


def get_time_mem(txt):
    if len(RES_MEAS) > 0:
        time_pat = r"^Elapsed Time \(s\): (\d+\.\d+|\d+)$"
        mem_pat = r"^Peak Memory \(kB\): (\d+\.\d+|\d+)$"
        elapsed = re.search(time_pat, txt, re.MULTILINE).group(1)
        mem = re.search(mem_pat, txt, re.MULTILINE).group(1)
        return round(float(elapsed), 3), round(float(mem) / 1000)
    return 0.0, 0.0


def launch_process(cmd, *args, **kwargs):
    cmd = RES_MEAS + cmd
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        *args,
        **kwargs,
    ) as proc:
        try:
            proc.wait(TIMEOUT_S)
            if proc.returncode != 0:
                print(proc.stderr.read())
                raise subprocess.CalledProcessError(proc.returncode, cmd)
            return (proc.stdout.read(), proc.stderr.read())
        except subprocess.TimeoutExpired as te:
            print(f"Timeout reached after {TIMEOUT_S}s, computation aborted")
            proc.terminate()
            raise te


def store_log(log, ds_name, app):
    file_name = f"logs/{ds_name}.{app}.log"
    with open(file_name, "w") as dst:
        dst.write(log)


def compute_ttk(fname, times, dipha_offload=False, hybrid_pp=False, one_thread=False):
    dataset = dataset_name(fname)
    if dipha_offload:
        if hybrid_pp:
            print("Processing " + dataset + " with TTK-sandwich/Dipha...")
        else:
            print("Processing " + dataset + " with TTK/Dipha...")
    else:
        print("Processing " + dataset + " with TTK-sandwich...")
    outp = f"diagrams/{dataset}.vtu"
    cmd = ["ttkPersistenceDiagramCmd", "-i", fname, "-d", "4", "-a", "ImageFile_Order"]
    if one_thread:
        cmd.extend(["-t", "1"])
    key = "ttk-sandwich"
    if dipha_offload:
        cmd.append("-wd")
        key = "ttk/dipha"
        if hybrid_pp:
            cmd.append("-dpp")
            key = "ttk-sandwich/dipha"

    def ttk_compute_time(ttk_output):
        ttk_output = escape_ansi_chars(ttk_output)
        time_re = r"\[PersistenceDiagram\] Complete.*\[(\d+\.\d+|\d+)s"
        cpt_time = float(re.search(time_re, ttk_output, re.MULTILINE).group(1))
        overhead = ttk_overhead_time(ttk_output)
        return cpt_time - overhead

    def ttk_prec_time(ttk_output):
        ttk_output = escape_ansi_chars(ttk_output)
        prec_re = (
            r"\[PersistenceDiagram\] Precondition triangulation.*\[(\d+\.\d+|\d+)s"
        )
        prec_time = float(re.search(prec_re, ttk_output, re.MULTILINE).group(1))
        return prec_time

    def ttk_overhead_time(ttk_output):
        time_re = (
            r"\[DiscreteGradient\] Wrote Dipha explicit complex.*\[(\d+\.\d+|\d+)s"
        )
        try:
            return float(re.search(time_re, ttk_output, re.MULTILINE).group(1))
        except AttributeError:
            return 0.0

    try:
        out, err = launch_process(cmd)
        elapsed, mem = get_time_mem(err)
        times[dataset][key] = {
            "prec": ttk_prec_time(out),
            "pers": ttk_compute_time(out),
            "mem": mem,
        }
        os.rename("output_port_0.vtu", outp)
        times[dataset][key] |= get_pairs_number(outp)
        store_log(out, dataset, key.replace("/", "_"))
        print(f"  Done in {elapsed}s")
    except subprocess.TimeoutExpired:
        pass

    try:
        os.remove("morse.dipha")
        os.remove("output.dipha")
    except FileNotFoundError:
        pass


def compute_dipha(fname, times, one_thread=False):
    dataset = dataset_name(fname)
    print("Processing " + dataset + " with Dipha...")
    outp = f"diagrams/{dataset}.dipha"
    cmd = ["build_dipha/dipha", "--benchmark", fname, outp]
    if not one_thread:
        cmd = ["mpirun", "--use-hwthread-cpus"] + cmd

    out, err = launch_process(cmd)

    def dipha_compute_time(dipha_output):
        run_pat = r"^Overall running time.*\n(\d+.\d+|\d+)$"
        run_time = re.search(run_pat, dipha_output, re.MULTILINE).group(1)
        run_time = float(run_time)
        read_pat = r"^ *(\d+.\d+|\d+)s.*complex.load_binary.*$"
        read_time = re.search(read_pat, dipha_output, re.MULTILINE).group(1)
        read_time = float(read_time)
        write_pat = r"^ *(\d+.\d+|\d+)s.*save_persistence_diagram.*$"
        write_time = re.search(write_pat, dipha_output, re.MULTILINE).group(1)
        write_time = float(write_time)
        prec = round(read_time + write_time, 3)
        pers = round(run_time - prec, 3)
        return prec, pers

    prec, pers = dipha_compute_time(out)
    elapsed, mem = get_time_mem(err)
    times[dataset]["dipha"] = {
        "prec": prec,
        "pers": pers,
        "mem": mem,
    }
    times[dataset]["dipha"] |= get_pairs_number(outp)
    print(f"  Done in {elapsed}s")
    store_log(out, dataset, "dipha")


def compute_cubrips(fname, times):
    dataset = dataset_name(fname)
    print("Processing " + dataset + " with CubicalRipser...")
    outp = f"diagrams/{dataset}.cr"
    cmd = ["CubicalRipser/CR3", fname, "--output", outp]

    try:
        _, err = launch_process(cmd)
        elapsed, mem = get_time_mem(err)
        times[dataset]["CubicalRipser"] = {
            "prec": 0.0,
            "pers": elapsed,
            "mem": mem,
        }
        times[dataset]["CubicalRipser"] |= get_pairs_number(outp)
        print(f"  Done in {elapsed}s")
    except subprocess.CalledProcessError:
        print(dataset + " is too large for CubicalRipser")
    except subprocess.TimeoutExpired:
        pass


def compute_gudhi_dionysus(fname, times, backend):
    dataset = dataset_name(fname)
    print(f"Processing {dataset} with {backend}...")
    outp = f"diagrams/{dataset}_{backend}.gudhi"

    def compute_time(output):
        prec_pat = r"^Filled filtration.*: (\d+.\d+|\d+)s$"
        pers_pat = r"^Computed persistence.*: (\d+.\d+|\d+)s$"
        try:
            prec = re.search(prec_pat, output, re.MULTILINE).group(1)
            prec = round(float(prec), 3)
        except AttributeError:
            # Gudhi for cubical complexes has no precondition time
            prec = 0.0
        pers = re.search(pers_pat, output, re.MULTILINE).group(1)
        pers = round(float(pers), 3)
        return (prec, pers)

    cmd = (
        ["python3", "dionysus_gudhi_persistence.py"]
        + ["-i", fname]
        + ["-o", outp]
        + ["-b", backend.lower()]
    )

    try:
        out, err = launch_process(cmd)
        prec, pers = compute_time(out)
        elapsed, mem = get_time_mem(err)
        times[dataset][backend] = {
            "prec": prec,
            "pers": pers,
            "mem": mem,
        }
        times[dataset][backend] |= get_pairs_number(outp)
        print(f"  Done in {elapsed}s")
    except subprocess.TimeoutExpired:
        pass


def compute_oineus(fname, times, one_thread=False):
    dataset = dataset_name(fname)
    print(f"Processing {dataset} with Oineus...")
    outp = f"diagrams/{dataset}_Oineus.gudhi"

    def oineus_compute_time(oineus_output):
        pat = r"matrix reduced in (\d+.\d+|\d+)"
        pers_time = re.search(pat, oineus_output).group(1)
        return round(float(pers_time), 3)

    # launch with subprocess to capture stdout from the C++ library
    cmd = ["python3", "oineus_persistence.py", fname, "-o", outp]
    if not one_thread:
        cmd.extend(["-t", str(multiprocessing.cpu_count())])

    try:
        _, err = launch_process(cmd)
        pers = oineus_compute_time(err)
        elapsed, mem = get_time_mem(err)
        times[dataset]["Oineus"] = {
            "prec": round(elapsed - pers, 3),
            "pers": pers,
            "mem": mem,
        }
        times[dataset]["Oineus"] |= get_pairs_number(outp)
        print(f"  Done in {elapsed}s")
    except subprocess.TimeoutExpired:
        pass


def compute_diamorse(fname, times):
    dataset = dataset_name(fname)
    print("Processing " + dataset + " with Diamorse...")
    outp = f"diagrams/{dataset}_Diamorse.gudhi"
    cmd = ["python2", "diamorse/python/persistence.py", fname, "-r"]

    try:
        out, err = launch_process(cmd, env=dict())  # reset environment for Python2
        elapsed, mem = get_time_mem(err)
        times[dataset]["Diamorse"] = {
            "prec": 0.0,
            "pers": elapsed,
            "mem": mem,
        }

        # convert output to Gudhi format on-the-fly
        pairs = list()
        for line in out.splitlines():
            if line.startswith("#"):
                continue
            pairs.append(line.split()[:3])
        with open(outp, "w") as dst:
            for birth, death, dim in pairs:
                dst.write(f"{dim} {birth} {death}\n")

        times[dataset]["Diamorse"] |= get_pairs_number(outp)
        print(f"  Done in {elapsed}s")
    except subprocess.TimeoutExpired:
        pass


def compute_perseus(fname, times, simplicial):
    dataset = dataset_name(fname)
    print("Processing " + dataset + " with Perseus...")
    outp = f"diagrams/{dataset}_Perseus.gudhi"
    subc = "simtop" if simplicial else "cubtop"
    cmd = ["perseus/perseus", subc, fname, "out"]

    try:
        _, err = launch_process(cmd)
        elapsed, mem = get_time_mem(err)
        times[dataset]["Perseus"] = {
            "prec": 0.0,
            "pers": elapsed,
            "mem": mem,
        }

        # convert output to Gudhi format
        pers2gudhi.main("out", outp)

        times[dataset]["Perseus"] |= get_pairs_number(outp)
        print(f"  Done in {elapsed}s")
    except subprocess.TimeoutExpired:
        pass


def compute_eirene(fname, times):
    dataset = dataset_name(fname)
    print("Processing " + dataset + " with Eirene.jl...")
    outp = f"diagrams/{dataset}_Eirene.gudhi"
    cmd = ["julia", "call_eirene.jl", fname, outp]

    def compute_pers_time(output):
        pers_pat = r"^ (\d+.\d+|\d+) seconds.*$"
        pers = re.search(pers_pat, output, re.MULTILINE).group(1)
        pers = round(float(pers), 3)
        return pers

    try:
        out, err = launch_process(cmd)
        elapsed, mem = get_time_mem(err)
        pers = compute_pers_time(out)
        times[dataset]["Eirene"] = {
            "prec": round(elapsed - pers, 3),
            "pers": pers,
            "mem": mem,
        }

        times[dataset]["Eirene"] |= get_pairs_number(outp)
        print(f"  Done in {elapsed}s")
    except subprocess.TimeoutExpired:
        pass
    except subprocess.CalledProcessError:
        print(">> Consider installing Julia and Eirene.jl")


def compute_diagrams(args):

    # output diagrams directory
    create_dir("diagrams")
    # log directory
    create_dir("logs")

    # store computation times
    times = dict()

    one_thread = args.sequential

    global TIMEOUT_S
    TIMEOUT_S = args.timeout

    for fname in sorted(glob.glob("datasets/*")):
        # initialize compute times table
        dsname = dataset_name(fname)
        times[dsname] = {"#Threads": 1 if one_thread else multiprocessing.cpu_count()}
        times[dsname]["#Vertices"] = dsname.split("_")[-4]

    for fname in sorted(glob.glob("datasets/*")):
        ext = fname.split(".")[-1]
        if ext in ("vtu", "vti"):
            # our algo
            compute_ttk(fname, times, one_thread=one_thread)
            # ttk-hybrid: offload Morse-Smale complex to Dipha
            compute_ttk(fname, times, dipha_offload=True, one_thread=one_thread)
            # ttk-hybrid++: offload saddle connectors to Dipha
            compute_ttk(
                fname, times, dipha_offload=True, hybrid_pp=True, one_thread=one_thread
            )
        elif ext == "dipha":
            compute_dipha(fname, times, one_thread)
            if "impl" in fname:
                compute_cubrips(fname, times)
        elif ext == "pers" and "impl" in fname:
            compute_gudhi_dionysus(fname, times, "Gudhi")
            compute_oineus(fname, times, one_thread)
            compute_perseus(fname, times, False)
        elif ext == "pers" and "expl" in fname:
            compute_perseus(fname, times, True)
        elif ext == "tsc":
            compute_gudhi_dionysus(fname, times, "Gudhi")
            compute_gudhi_dionysus(fname, times, "Dionysus")
            # compute_gudhi_dionysus(fname, times, "Ripser")
        elif ext == "nc":
            compute_diamorse(fname, times)
        elif ext == "eirene":
            compute_eirene(fname, times)

        # write partial results after every dataset computation
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
            proc0 = subprocess.run(cmd, capture_output=True, check=True)
            cmd = ["python", "ttk_distance.py", method, dipha_diag, empty_diag]
            print(f"Computing Dipha distance to empty diagram for {ds}")
            proc1 = subprocess.run(cmd, capture_output=True, check=True)

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
    prep_datasets.add_argument(
        "-d",
        "--download",
        help="Download raw files from OpenSciViz",
        action="store_true",
    )
    prep_datasets.add_argument(
        "-s",
        "--max_dataset_size",
        help="Maximum size of the raw files to download (MB)",
        type=int,
        default=download_datasets.SIZE_LIMIT_MB,
    )
    prep_datasets.add_argument(
        "-r",
        "--max_resample_size",
        help="Maximum size of the resampled datasets (vertices per edge)",
        type=int,
        default=convert_datasets.RESAMPL,
    )
    prep_datasets.set_defaults(func=prepare_datasets)

    get_diags = subparsers.add_parser("compute_diagrams")
    get_diags.add_argument(
        "-1",
        "--sequential",
        help="Disable the multi-threading support",
        action="store_true",
    )
    get_diags.add_argument(
        "-t",
        "--timeout",
        help="Timeout in seconds of every persistence diagram computation",
        type=int,
    )
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

#!/usr/bin/env python3

import argparse
import glob
import json
import multiprocessing
import os
import re
import resource
import subprocess

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
RES_MEAS = ["/usr/bin/time", "-f", "Elapsed Time (s): %e\nPeak Memory (kB): %M"]


def get_time_mem(txt):
    time_pat = r"^Elapsed Time \(s\): (\d+\.\d+|\d+)$"
    mem_pat = r"^Peak Memory \(kB\): (\d+\.\d+|\d+)$"
    elapsed = re.search(time_pat, txt, re.MULTILINE).group(1)
    mem = re.search(mem_pat, txt, re.MULTILINE).group(1)
    return round(float(elapsed), 3), round(float(mem) / 1000)


def store_log(log, ds_name, app):
    file_name = f"logs/{ds_name}.{app}.log"
    with open(file_name, "w") as dst:
        dst.write(log.decode())


def compute_ttk(fname, times, dipha_offload=False, hybrid_pp=False, one_thread=False):
    dataset = dataset_name(fname)
    if dipha_offload:
        if hybrid_pp:
            print("Processing " + dataset + " with TTK (hybrid++ mode)...")
        else:
            print("Processing " + dataset + " with TTK (hybrid mode)...")
    else:
        print("Processing " + dataset + " with TTK...")
    outp = f"diagrams/{dataset}.vtu"
    cmd = ["ttkPersistenceDiagramCmd", "-i", fname, "-d", "4", "-a", "ImageFile_Order"]
    if one_thread:
        cmd.extend(["-t", "1"])
    key = "ttk"
    if dipha_offload:
        cmd.append("-wd")
        key = "ttk-hybrid"
        if hybrid_pp:
            cmd.append("-dpp")
            key = "ttk-hybrid++"

    cmd = RES_MEAS + cmd

    def ttk_compute_time(ttk_output):
        ttk_output = escape_ansi_chars(ttk_output.decode())
        time_re = r"\[PersistenceDiagram\] Complete.*\[(\d+\.\d+|\d+)s"
        cpt_time = float(re.search(time_re, ttk_output, re.MULTILINE).group(1))
        overhead = ttk_overhead_time(ttk_output)
        return cpt_time - overhead

    def ttk_prec_time(ttk_output):
        ttk_output = escape_ansi_chars(ttk_output.decode())
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
        proc = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT_S, check=True)
        times[dataset][key] = {
            "prec": ttk_prec_time(proc.stdout),
            "pers": ttk_compute_time(proc.stdout),
            "mem": get_time_mem(proc.stderr.decode())[1],
        }
        os.rename("output_port_0.vtu", outp)
        ttk_dipha_print_pairs(outp)
        store_log(proc.stdout, dataset, key)
    except subprocess.TimeoutExpired:
        print("Timeout reached, computation aborted")


def compute_dipha(fname, times, one_thread=False):
    dataset = dataset_name(fname)
    print("Processing " + dataset + " with dipha...")
    outp = f"diagrams/{dataset}.dipha"
    cmd = ["build_dipha/dipha", "--benchmark", fname, outp]
    if not one_thread:
        cmd = ["mpirun", "--use-hwthread-cpus"] + cmd
    cmd = RES_MEAS + cmd
    proc = subprocess.run(cmd, capture_output=True, check=True)  # no timeout here?

    def dipha_compute_time(dipha_output):
        dipha_output = dipha_output.decode()
        run_pat = r"^Overall running time.*\n(\d+.\d+|\d+)$"
        run_time = re.search(run_pat, dipha_output, re.MULTILINE).group(1)
        run_time = float(run_time)
        pers_pat = r"^Reduction kernel running time.*\n(\d+.\d+|\d+)$"
        pers_time = re.search(pers_pat, dipha_output, re.MULTILINE).group(1)
        pers_time = float(pers_time)
        return round(run_time - pers_time, 3), round(pers_time, 3)

    ret = ttk_dipha_print_pairs(outp)
    times[dataset] |= ret
    prec, pers = dipha_compute_time(proc.stdout)
    times[dataset]["dipha"] = {
        "prec": prec,
        "pers": pers,
        "mem": get_time_mem(proc.stderr.decode())[1],
    }
    store_log(proc.stdout, dataset, "dipha")


def compute_cubrips(fname, times):
    dataset = dataset_name(fname)
    print("Processing " + dataset + " with CubicalRipser...")
    outp = f"diagrams/{dataset}.cr"
    cmd = ["CubicalRipser/CR3", fname, "--output", outp]
    cmd = RES_MEAS + cmd

    try:
        proc = subprocess.run(cmd, timeout=TIMEOUT_S, capture_output=True, check=True)
        pers, mem = get_time_mem(proc.stderr.decode())
        times[dataset]["CubicalRipser"] = {
            "prec": 0.0,
            "pers": pers,
            "mem": mem,
        }
        ttk_dipha_print_pairs(outp)
    except subprocess.CalledProcessError:
        print(dataset + " is too large for CubicalRipser")
    except subprocess.TimeoutExpired:
        print("Timeout reached, computation aborted")


def compute_gudhi_dionysus(fname, times, backend):
    dataset = dataset_name(fname)
    print(f"Processing {dataset} with {backend}...")
    outp = f"diagrams/{dataset}_{backend}.gudhi"
    simplicial = not ("pers" in fname and "impl" in fname)

    def worker(args, retqueue):
        import dionysus_gudhi_persistence

        prec, pers = dionysus_gudhi_persistence.run(*args)
        mem = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000)
        retqueue.put((prec, pers, mem))

    queue = multiprocessing.Queue()
    # wrap calls to Python script in Process to clean memory
    p = multiprocessing.Process(
        target=worker, args=((fname, outp, backend, simplicial), queue)
    )
    p.start()
    p.join(TIMEOUT_S)

    if p.exitcode is not None:
        prec, pers, mem = queue.get()
        times[dataset][backend] = {
            "prec": prec,
            "pers": pers,
            "mem": mem,
        }
        ttk_dipha_print_pairs(outp)
    else:
        p.terminate()
        print("Timeout reached, computation aborted")


def compute_oineus(fname, times, one_thread=False):
    dataset = dataset_name(fname)
    print(f"Processing {dataset} with Oineus...")
    outp = f"diagrams/{dataset}_Oineus.gudhi"

    def oineus_compute_time(oineus_output):
        oineus_output = oineus_output.decode()
        pat = r"matrix reduced in (\d+.\d+|\d+)"
        pers_time = re.search(pat, oineus_output).group(1)
        return round(float(pers_time), 3)

    # launch with subprocess to capture stdout from the C++ library
    cmd = ["python3", "oineus_persistence.py", fname, "-o", outp]
    if not one_thread:
        cmd.extend(["-t", str(multiprocessing.cpu_count())])
    cmd = RES_MEAS + cmd

    try:
        proc = subprocess.run(cmd, capture_output=True, check=True, timeout=TIMEOUT_S)
        pers = oineus_compute_time(proc.stderr)
        elapsed, mem = get_time_mem(proc.stderr.decode())
        times[dataset]["Oineus"] = {
            "prec": round(elapsed - pers, 3),
            "pers": pers,
            "mem": mem,
        }
        ttk_dipha_print_pairs(outp)
    except subprocess.TimeoutExpired:
        print("Timeout reached, computation aborted")


def compute_diamorse(fname, times):
    dataset = dataset_name(fname)
    print("Processing " + dataset + " with Diamorse...")
    outp = f"diagrams/{dataset}.gudhi"
    cmd = ["python2", "diamorse/python/persistence.py", fname, "-r"]
    cmd = RES_MEAS + cmd

    try:
        proc = subprocess.run(cmd, timeout=TIMEOUT_S, capture_output=True, check=True)
        elapsed, mem = get_time_mem(proc.stderr.decode())
        times[dataset]["Diamorse"] = {
            "prec": 0.0,
            "pers": elapsed,
            "mem": mem,
        }

        # convert output to Gudhi format on-the-fly
        pairs = list()
        for line in proc.stdout.decode().splitlines():
            if line.startswith("#"):
                continue
            pairs.append(line.split()[:3])
        with open(outp, "w") as dst:
            for birth, death, dim in pairs:
                dst.write(f"{dim} {birth} {death}\n")

        ttk_dipha_print_pairs(outp)
    except subprocess.TimeoutExpired:
        print("Timeout reached, computation aborted")


def compute_diagrams(_):

    # output diagrams directory
    create_dir("diagrams")
    # log directory
    create_dir("logs")

    # store computation times
    times = dict()

    one_thread = False

    for fname in sorted(glob.glob("datasets/*")):
        # initialize compute times table
        times[dataset_name(fname)] = {
            "#Threads": 1 if one_thread else multiprocessing.cpu_count()
        }
        times[dataset_name(fname)]["#Vertices"] = "x".join(
            [str(convert_datasets.RESAMPL)] * 3
        )

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
        elif ext == "dipha" and "impl" in fname:
            compute_cubrips(fname, times)
        elif ext == "pers" and "impl" in fname:
            compute_gudhi_dionysus(fname, times, "Gudhi")
            compute_oineus(fname, times, one_thread)
        elif ext == "tsc":
            compute_gudhi_dionysus(fname, times, "Gudhi")
            compute_gudhi_dionysus(fname, times, "Dionysus")
            # compute_gudhi_dionysus(fname, times, "Ripser")
        elif ext == "nc":
            compute_diamorse(fname, times)

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

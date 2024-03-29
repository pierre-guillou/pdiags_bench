#!/usr/bin/env python3

import argparse
import datetime
import enum
import glob
import json
import logging
import multiprocessing
import os
import pathlib
import re
import subprocess
import sys

import download_datasets
import gudhi_diag_inf
import pers2gudhi

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)


def create_dir(dirname):
    try:
        os.mkdir(dirname)
    except FileExistsError:
        pass


# pylint: disable=import-outside-toplevel


def prepare_datasets(args):
    import convert_datasets
    import gen_random
    from convert_datasets import SliceType

    create_dir("raws")
    if args.download:
        download_datasets.main(args.max_dataset_size)

    # also generate a random and an elevation datasets
    for field in ["elevation", "random"]:
        gen_random.main(192, field, "raws")

    if not args.only_cubes and not args.only_slices and not args.only_lines:
        args.only_cubes = True
        args.only_slices = True
        args.only_lines = True

    create_dir("datasets")
    for dataset in sorted(glob.glob("raws/*.raw") + glob.glob("raws/*.vti")):
        # reduce RAM usage by isolating datasets manipulation in
        # separate processes
        if args.only_cubes:
            # 3D cubes
            if args.max_resample_size is None:
                rs = convert_datasets.RESAMPL_3D
            else:
                rs = args.max_resample_size
            p = multiprocessing.Process(
                target=convert_datasets.main,
                args=(dataset, "datasets", rs, SliceType.VOL),
            )
            p.start()
            p.join()
        if args.only_slices:
            # 2D slices
            if args.max_resample_size is None:
                rs = convert_datasets.RESAMPL_2D
            else:
                rs = args.max_resample_size
            p = multiprocessing.Process(
                target=convert_datasets.main,
                args=(dataset, "datasets", rs, SliceType.SURF),
            )
            p.start()
            p.join()
        if args.only_lines:
            # 1D lines
            if args.max_resample_size is None:
                rs = convert_datasets.RESAMPL_1D
            else:
                rs = args.max_resample_size
            p = multiprocessing.Process(
                target=convert_datasets.main,
                args=(dataset, "datasets", rs, SliceType.LINE),
            )
            p.start()
            p.join()


def get_pairs_number(diag):
    import compare_diags

    default = {
        "#Min-saddle": 0,
        "#Saddle-saddle": 0,
        "#Saddle-max": 0,
        "#Total pairs": 0,
    }

    try:
        pairs = compare_diags.read_diag(diag)
    except AttributeError:
        return default
    if len(pairs) == 0:
        return default

    if "x1_" in diag:
        # 2D
        return {
            "#Min-saddle": len(pairs[0]),
            "#Saddle-max": len(pairs[1]),
            "#Total pairs": sum([len(p) for p in pairs]),
        }
    # 3D
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
SEQUENTIAL = False  # parallel
RESUME = False  # compute every diagram


def get_time_mem(txt):
    try:
        time_pat = r"^Elapsed Time \(s\): (\d+\.\d+|\d+)$"
        mem_pat = r"^Peak Memory \(kB\): (\d+\.\d+|\d+)$"
        elapsed = re.search(time_pat, txt, re.MULTILINE).group(1)
        mem = re.search(mem_pat, txt, re.MULTILINE).group(1)
        return round(float(elapsed), 3), round(float(mem) / 1000)
    except AttributeError:
        return 0.0, 0.0


def launch_process(cmd, *args, **kwargs):
    RES_MEAS = [
        "/usr/bin/python3",
        "subprocess_wrapper.py",
        "--",
        "/usr/bin/timeout",
        "--preserve-status",
        str(TIMEOUT_S),
    ]
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
                logging.debug(proc.stderr.read())
                raise subprocess.CalledProcessError(proc.returncode, cmd)
            return (proc.stdout.read(), proc.stderr.read())
        except subprocess.TimeoutExpired as te:
            proc.terminate()
            raise te


def store_log(log, ds_name, app, nthreads=None):
    thrs = f".{nthreads}T" if nthreads is not None else ""
    file_name = f"logs/{ds_name}.{app}{thrs}.log"
    with open(file_name, "w") as dst:
        dst.write(log)


class SoftBackend(enum.Enum):
    TTK_FTM = "TTK-FTM"
    DISCRETE_MORSE_SANDWICH = "DiscreteMorseSandwich"
    DIPHA = "Dipha"
    DIPHA_MPI = "Dipha_MPI"
    CUBICALRIPSER = "CubicalRipser"
    GUDHI = "Gudhi"
    PERSEUS_CUB = "Perseus_cubtop"
    PERSEUS_SIM = "Perseus_simtop"
    DIONYSUS = "Dionysus"
    RIPSER = "Ripser"
    OINEUS = "Oineus"
    OINEUS_SIMPL = "Oineus"
    DIAMORSE = "Diamorse"
    EIRENE = "Eirene.jl"
    JAVAPLEX = "JavaPlex"
    PHAT_SPECTR_SEQ = "PHAT_spectral_sequence"
    PHAT_CHUNK = "PHAT_chunk"
    PERSCYCL = "PersistenceCycles"

    def get_compute_function(self):
        dispatcher = {
            SoftBackend.TTK_FTM: compute_ttk,
            SoftBackend.DISCRETE_MORSE_SANDWICH: compute_ttk,
            SoftBackend.DIPHA: compute_dipha,
            SoftBackend.DIPHA_MPI: compute_dipha,
            SoftBackend.CUBICALRIPSER: compute_cubrips,
            SoftBackend.PERSEUS_CUB: compute_perseus,
            SoftBackend.PERSEUS_SIM: compute_perseus,
            SoftBackend.GUDHI: compute_gudhi_dionysus,
            SoftBackend.DIONYSUS: compute_gudhi_dionysus,
            SoftBackend.RIPSER: compute_gudhi_dionysus,
            SoftBackend.OINEUS: compute_oineus,
            SoftBackend.OINEUS_SIMPL: compute_oineus_simpl,
            SoftBackend.DIAMORSE: compute_diamorse,
            SoftBackend.EIRENE: compute_eirene,
            SoftBackend.JAVAPLEX: compute_javaplex,
            SoftBackend.PHAT_SPECTR_SEQ: compute_phat,
            SoftBackend.PHAT_CHUNK: compute_phat,
            SoftBackend.PERSCYCL: compute_persistenceCycles,
        }
        return dispatcher[self]


class FileType(enum.Enum):
    VTI = enum.auto()
    VTU = enum.auto()
    DIPHA_CUB = enum.auto()
    DIPHA_TRI = enum.auto()
    PERS_CUB = enum.auto()
    PERS_TRI = enum.auto()
    TSC = enum.auto()
    NETCDF = enum.auto()
    EIRENE_CSV = enum.auto()
    PHAT_ASCII = enum.auto()
    OIN = enum.auto()
    UNDEFINED = enum.auto()

    # pylint: disable=R0911
    @classmethod
    def from_filename(cls, fname, complex_type):
        # get file type variant according to file extension and complex type
        ext = fname.split(".")[-1]

        if ext == "vti":
            return cls.VTI
        if ext == "vtu":
            return cls.VTU
        if ext == "dipha":
            if complex_type == Complex.CUBICAL:
                return cls.DIPHA_CUB
            if complex_type == Complex.SIMPLICIAL:
                return cls.DIPHA_TRI
        if ext == "pers":
            if complex_type == Complex.CUBICAL:
                return cls.PERS_CUB
            if complex_type == Complex.SIMPLICIAL:
                return cls.PERS_TRI
        if ext == "tsc":
            return cls.TSC
        if ext == "nc":
            return cls.NETCDF
        if ext == "eirene":
            return cls.EIRENE_CSV
        if ext == "phat":
            return cls.PHAT_ASCII
        if ext == "oin":
            return cls.OIN

        return cls.UNDEFINED

    def get_backends(self, slice_type):
        from convert_datasets import SliceType

        partial = pathlib.Path(".not_all_apps").exists()

        # get backends list from file type variant and slice types
        if self in [FileType.VTI, FileType.VTU]:
            if slice_type in [SliceType.SURF, SliceType.VOL]:
                # FTM + our algo in 2D and 3D
                ret = [SoftBackend.TTK_FTM, SoftBackend.DISCRETE_MORSE_SANDWICH]
                if not partial:
                    ret.append(SoftBackend.PERSCYCL)
                return ret
            return [SoftBackend.DISCRETE_MORSE_SANDWICH]  # 1D lines
        if self == FileType.DIPHA_CUB:
            return [SoftBackend.DIPHA, SoftBackend.DIPHA_MPI, SoftBackend.CUBICALRIPSER]
        if self == FileType.DIPHA_TRI:
            if slice_type == SliceType.LINE:
                return [SoftBackend.DIPHA]
            return [SoftBackend.DIPHA, SoftBackend.DIPHA_MPI]
        if self == FileType.PERS_CUB:
            return [SoftBackend.GUDHI, SoftBackend.OINEUS, SoftBackend.PERSEUS_CUB]
        if self == FileType.PERS_TRI:
            return []  # disable Perseus for simplicial complexes
            # return [SoftBackend.PERSEUS_SIM]
        if self == FileType.TSC:
            ret = [SoftBackend.GUDHI]
            if not partial:
                ret += [SoftBackend.DIONYSUS, SoftBackend.JAVAPLEX]
                if slice_type in (SliceType.SURF, SliceType.LINE):
                    return ret + [SoftBackend.RIPSER]  # Ripser only in 2D
            if slice_type == SliceType.VOL:
                return ret
        if self == FileType.NETCDF:
            return [SoftBackend.DIAMORSE]
        if self == FileType.EIRENE_CSV:
            return [SoftBackend.EIRENE]
        if self == FileType.PHAT_ASCII:
            return [SoftBackend.PHAT_SPECTR_SEQ, SoftBackend.PHAT_CHUNK]
        if self == FileType.OIN:
            return [SoftBackend.OINEUS_SIMPL]

        return []


class Complex(enum.Enum):
    CUBICAL = enum.auto()
    SIMPLICIAL = enum.auto()
    UNDEFINED = enum.auto()

    @classmethod
    def from_filename(cls, fname):
        if "impl" in fname:
            return cls.CUBICAL
        if "expl" in fname:
            return cls.SIMPLICIAL
        return cls.UNDEFINED


def parallel_decorator(func):
    def wrapper(*args, **kwargs):
        if not SEQUENTIAL:
            nt = multiprocessing.cpu_count()
            logging.info("  Parallel implementation (%s threads)", nt)
            el = func(*args, **kwargs, num_threads=nt)
            logging.info("  Done in %.3fs", el)
        logging.info("  Sequential implementation")
        return func(*args, **kwargs, num_threads=1)

    return wrapper


@parallel_decorator
def compute_ttk(fname, times, backend, num_threads=1):
    dataset = dataset_name(fname)
    bs = backend.value.replace("/", "-")
    outp = f"diagrams/{dataset}_{bs}.vtu"
    cmd = (
        ["build_dirs/install_paraview_v5.10.1/bin/ttkPersistenceDiagramCmd"]
        + ["-i", fname]
        + ["-d", "4"]
        + ["-a", "ImageFile_Order"]
        + ["-t", str(num_threads)]
    )

    if backend == SoftBackend.TTK_FTM:
        cmd += ["-B", "0"]
    elif backend == SoftBackend.DISCRETE_MORSE_SANDWICH:
        cmd += ["-B", "2"]

    def ttk_compute_time(ttk_output):
        ttk_output = escape_ansi_chars(ttk_output)
        time_re = r"\[PersistenceDiagram.*\] Complete.*\[(\d+\.\d+|\d+)s"
        cpt_time = float(re.search(time_re, ttk_output, re.MULTILINE).group(1))
        overhead = ttk_overhead_time(ttk_output, backend)
        return cpt_time - overhead

    def ttk_prec_time(ttk_output):
        ttk_output = escape_ansi_chars(ttk_output)
        prec_re = (
            r"\[PersistenceDiagram.*\] Precondition triangulation.*\[(\d+\.\d+|\d+)s"
        )
        prec_time = float(re.search(prec_re, ttk_output, re.MULTILINE).group(1))
        return prec_time

    def ttk_overhead_time(ttk_output, backend):
        if backend == SoftBackend.DISCRETE_MORSE_SANDWICH:
            time_re = r"\[DiscreteGradient.*\] Memory allocations.*\[(\d+\.\d+|\d+)s"
        elif backend == SoftBackend.TTK_FTM:
            time_re = r"\[FTMTree.*\] alloc.*\[(\d+\.\d+|\d+)s"
        try:
            return float(re.search(time_re, ttk_output, re.MULTILINE).group(1))
        except AttributeError:
            return 0.0

    out, err = launch_process(cmd)
    elapsed, mem = get_time_mem(err)
    res = {
        "prec": round(ttk_prec_time(out), 3),
        "pers": round(ttk_compute_time(out), 3),
        "mem": mem,
        "#threads": num_threads,
    }
    os.rename("output_port_0.vtu", outp)
    res.update(get_pairs_number(outp))
    times[dataset].setdefault(backend.value, {}).update(
        {("seq" if num_threads == 1 else "para"): res}
    )

    store_log(out, dataset, bs, num_threads)

    try:
        os.remove("morse.dipha")
        os.remove("output.dipha")
    except FileNotFoundError:
        pass

    return elapsed


def compute_dipha(fname, times, backend):
    dataset = dataset_name(fname)
    b = backend.value.split("_")[0]
    outp = f"diagrams/{dataset}_{b}.dipha"
    cmd = ["build_dirs/dipha/dipha", "--benchmark", fname, outp]
    num_threads = 1
    if backend is SoftBackend.DIPHA_MPI:
        num_threads = multiprocessing.cpu_count()
        cmd = ["mpirun", "--use-hwthread-cpus", "-np", str(num_threads)] + cmd

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

    def dipha_mem_peak(dipha_output):
        mem_pat = r"^Global peak mem \(MB\): (\d+.\d+|\d+)$"
        mem_peak = re.search(mem_pat, dipha_output, re.MULTILINE).group(1)
        mem_peak = float(mem_peak)
        return mem_peak

    prec, pers = dipha_compute_time(out)
    elapsed, _ = get_time_mem(err)
    res = {
        "prec": prec,
        "pers": pers,
        "mem": dipha_mem_peak(out),
        "#threads": num_threads,
    }
    res.update(get_pairs_number(outp))
    times[dataset].setdefault(b, {}).update(
        {("seq" if num_threads == 1 else "para"): res}
    )
    store_log(out, dataset, "dipha", num_threads)
    return elapsed


def compute_cubrips(fname, times, backend):
    dataset = dataset_name(fname)
    outp = f"diagrams/{dataset}_{backend.value}.dipha"
    if "x1_" in dataset:
        binary = "CubicalRipser_2dim/CR2"
    else:
        binary = "CubicalRipser_3dim/CR3"
    cmd = (
        [f"backends_src/{binary}"]
        + ["--output", outp]
        + ["--method", "compute_pairs"]
        + [fname]
    )

    _, err = launch_process(cmd)
    elapsed, mem = get_time_mem(err)
    res = {
        "prec": 0.0,
        "pers": elapsed,
        "mem": mem,
    }
    res.update(get_pairs_number(outp))
    times[dataset][backend.value] = {"seq": res}
    return elapsed


def compute_gudhi_dionysus(fname, times, backend):
    dataset = dataset_name(fname)
    backend = backend.value
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

    out, err = launch_process(cmd)
    prec, pers = compute_time(out)
    elapsed, mem = get_time_mem(err)
    res = {
        "prec": prec,
        "pers": pers,
        "mem": mem,
    }
    res.update(get_pairs_number(outp))
    if backend == "Gudhi":
        res.update({"#threads": multiprocessing.cpu_count()})
        times[dataset][backend] = {"para": res}
    else:
        times[dataset][backend] = {"seq": res}
    return elapsed


@parallel_decorator
def compute_oineus(fname, times, backend, num_threads=1):
    dataset = dataset_name(fname)
    outp = f"diagrams/{dataset}_{backend.value}.gudhi"

    def oineus_compute_time(oineus_output):
        pat = r"matrix reduced in (\d+.\d+|\d+)"
        pers_time = re.search(pat, oineus_output).group(1)
        return round(float(pers_time), 3)

    # launch with subprocess to capture stdout from the C++ library
    cmd = ["python3", "oineus_persistence.py", fname, "-o", outp]
    if num_threads > 1:
        cmd.extend(["-t", str(num_threads)])

    _, err = launch_process(cmd)
    pers = oineus_compute_time(err)
    elapsed, mem = get_time_mem(err)
    res = {
        "prec": round(elapsed - pers, 3),
        "pers": pers,
        "mem": mem,
        "#threads": num_threads,
    }
    res.update(get_pairs_number(outp))
    times[dataset].setdefault(backend.value, {}).update(
        {("seq" if num_threads == 1 else "para"): res}
    )

    return elapsed


@parallel_decorator
def compute_oineus_simpl(fname, times, backend, num_threads=1):
    dataset = dataset_name(fname)
    outp = f"diagrams/{dataset}_{backend.value}.gudhi"

    def oineus_compute_time(oineus_output):
        pat = r".*elapsed = (\d+.\d+|\d+) sec"
        pers_time = re.search(pat, oineus_output).group(1)
        return round(float(pers_time), 3)

    # launch with subprocess to capture stdout from the C++ library
    cmd = ["build_dirs/oineus/oineus_filtration", fname]
    if num_threads > 1:
        cmd.extend(["-t", str(num_threads)])

    out, err = launch_process(cmd)
    pers = oineus_compute_time(out)
    elapsed, mem = get_time_mem(err)
    res = {
        "prec": round(elapsed - pers, 3),
        "pers": pers,
        "mem": mem,
        "#threads": num_threads,
    }
    os.rename("diag.gudhi", outp)
    res.update(get_pairs_number(outp))
    times[dataset].setdefault(backend.value, {}).update(
        {("seq" if num_threads == 1 else "para"): res}
    )

    return elapsed


def compute_diamorse(fname, times, backend):
    dataset = dataset_name(fname)
    outp = f"diagrams/{dataset}_{backend.value}.gudhi"
    cmd = [
        "python2",
        "backends_src/diamorse/python/persistence.py",
        fname,
        "-r",
        "-o",
        outp,
    ]

    _, err = launch_process(cmd, env={})  # reset environment for Python2
    elapsed, mem = get_time_mem(err)
    res = {
        "prec": 0.0,
        "pers": elapsed,
        "mem": mem,
    }

    res.update(get_pairs_number(outp))
    times[dataset][backend.value] = {"seq": res}
    return elapsed


def compute_perseus(fname, times, backend):
    dataset = dataset_name(fname)
    outp = f"diagrams/{dataset}-{backend.value}.gudhi"
    subc = "simtop" if backend == SoftBackend.PERSEUS_SIM else "cubtop"
    cmd = ["backends_src/perseus/perseus", subc, fname]

    _, err = launch_process(cmd)
    elapsed, mem = get_time_mem(err)
    res = {
        "prec": 0.0,
        "pers": elapsed,
        "mem": mem,
    }

    # convert output to Gudhi format
    pers2gudhi.main("output", outp)

    res.update(get_pairs_number(outp))
    times[dataset][backend.value.split("_")[0]] = {"seq": res}
    return elapsed


def compute_eirene(fname, times, backend):
    dataset = dataset_name(fname)
    outp = f"diagrams/{dataset}_{backend.value}.gudhi"
    cmd = ["julia", "call_eirene.jl", fname, outp]

    def compute_pers_time(output):
        pers_pat = r"^(\d+.\d+|\d+) seconds.*$"
        pers = re.search(pers_pat, output, re.MULTILINE).group(1)
        pers = round(float(pers), 3)
        return pers

    out, err = launch_process(cmd)
    elapsed, mem = get_time_mem(err)
    pers = compute_pers_time(out)
    res = {
        "prec": round(elapsed - pers, 3),
        "pers": pers,
        "mem": mem,
    }

    res.update(get_pairs_number(outp))
    times[dataset][backend.value] = {"seq": res}
    return elapsed


def compute_javaplex(fname, times, backend):
    dataset = dataset_name(fname)
    outp = f"diagrams/{dataset}_{backend.value}.gudhi"
    cmd = (
        ["java", "-Xmx64G"]
        + ["-classpath", ".:backends_src/javaplex.jar"]
        + ["jplex_persistence", fname, outp]
    )

    def compute_pers_time(output):
        pers_pat = r"^.* (\d+.\d+|\d+) seconds$"
        pers = re.search(pers_pat, output, re.MULTILINE).group(1)
        pers = round(float(pers), 3)
        return pers

    out, err = launch_process(cmd)
    elapsed, mem = get_time_mem(err)
    pers = compute_pers_time(out)
    res = {
        "prec": round(elapsed - pers, 3),
        "pers": pers,
        "mem": mem,
        "#threads": multiprocessing.cpu_count(),
    }

    res.update(get_pairs_number(outp))
    times[dataset][backend.value] = {"para": res}
    return elapsed


@parallel_decorator
def compute_phat(fname, times, backend, num_threads=1):
    dataset = dataset_name(fname)
    outp = f"diagrams/{dataset}_{backend.value}.gudhi"
    cmd = [sys.executable, "phat2gudhi.py", "-o", outp, fname, "-t", str(num_threads)]
    if backend == SoftBackend.PHAT_CHUNK:
        cmd += ["-b", "chunk"]

    out, err = launch_process(cmd)

    def compute_pers_time(output):
        pers_pat = r"Computing persistence pairs took (\d+.\d+|\d+)s"
        pers = re.search(pers_pat, output, re.MULTILINE).group(1)
        pers = round(float(pers), 3)
        return pers

    elapsed, mem = get_time_mem(err)
    pers = compute_pers_time(out)
    res = {
        "prec": round(elapsed - pers, 3),
        "pers": pers,
        "mem": mem,
        "#threads": multiprocessing.cpu_count(),
    }

    res.update(get_pairs_number(outp))
    times[dataset].setdefault(backend.value, {}).update(
        {("seq" if num_threads == 1 else "para"): res}
    )
    return elapsed


@parallel_decorator
def compute_persistenceCycles(fname, times, backend, num_threads=1):
    dataset = dataset_name(fname)
    outp = f"diagrams/{dataset}_{backend.value}.gudhi"
    cmd = [
        sys.executable,
        "persistentCycles.py",
        fname,
        "-o",
        outp,
        "-t",
        str(num_threads),
    ]

    out, err = launch_process(cmd)

    def compute_pers_time(output):
        grad_pat = r"Gradient computed in (\d+.\d+|\d+) seconds"
        grad = re.search(grad_pat, output, re.MULTILINE).group(1)
        grad = round(float(grad), 3)
        pers_pat = r"Persistent homology computed in [+-]?(\d+([.]\d*)?(e[+-]?\d+)?|[.]\d+(e[+-]?\d+)?) seconds"
        pers = re.search(pers_pat, output, re.MULTILINE).group(1)
        pers = grad + round(float(pers), 3)
        return pers

    elapsed, mem = get_time_mem(err)
    pers = compute_pers_time(out)
    res = {
        "prec": round(elapsed - pers, 3),
        "pers": pers,
        "mem": mem,
        "#threads": num_threads,
    }

    res.update(get_pairs_number(outp))
    times[dataset].setdefault(backend.value, {}).update(
        {("seq" if num_threads == 1 else "para"): res}
    )
    return elapsed


def dispatch(fname, times):
    from convert_datasets import SliceType

    slice_type = SliceType.from_filename(fname)
    complex_type = Complex.from_filename(fname)
    file_type = FileType.from_filename(fname, complex_type)
    backends = file_type.get_backends(slice_type)

    for b in backends:
        dsname = dataset_name(fname)
        if RESUME and dsname in times and b.value in times[dsname]:
            logging.info("Skipping %s already processed by %s", dsname, b.value)
            return

        logging.info("Processing %s with %s...", fname.split("/")[-1], b.value)

        try:  # catch exception at every backend call

            # call backend compute function
            el = b.get_compute_function()(fname, times, b)

            logging.info("  Done in %.3fs", el)
        except subprocess.TimeoutExpired:
            logging.warning(
                "  Timeout reached after %ds, computation aborted", TIMEOUT_S
            )
            bv = b.value
            if "Perseus" in bv:
                bv = "Perseus"
            times[dsname].setdefault(bv.replace("_", "/"), {}).update(
                {"timeout": TIMEOUT_S}
            )
        except subprocess.CalledProcessError:
            logging.error("  Process aborted")
            times[dsname].setdefault(b.value, {}).update({"error": "abort"})


def compute_diagrams(args):

    # output diagrams directory
    create_dir("diagrams")
    # log directory
    create_dir("logs")

    # store computation times
    times = {}

    # pylint: disable=W0603
    global TIMEOUT_S
    TIMEOUT_S = args.timeout
    global SEQUENTIAL
    SEQUENTIAL = args.sequential
    global RESUME
    RESUME = args.resume is not None

    if RESUME:
        logging.info("Resuming computation from %s", args.resume)
        with open(args.resume) as src:
            times = json.load(src)

    result_fname = f"results_{datetime.datetime.now().isoformat()}.json"

    for fname in sorted(glob.glob("datasets/*")):
        if args.only_lines and "x1x1_" not in fname:
            continue
        if args.only_slices and ("x1_" not in fname or "x1x1_" in fname):
            continue
        if args.only_cubes and "x1_" in fname:
            continue

        # initialize compute times table
        dsname = dataset_name(fname)
        if times.get(dsname) is None:
            times[dsname] = {
                "#Vertices": dsname.split("_")[-3],
            }

        # call dispatch function per dataset
        dispatch(fname, times)

        # write partial results after every dataset computation
        with open(result_fname, "w") as dst:
            json.dump(times, dst, indent=4)

    # post-process generated Gudhi diagrams
    gudhi_diag_inf.main()
    return times


def compute_distances(args):
    import diagram_distance

    if args.method == "auction":
        distmeth = diagram_distance.DistMethod.AUCTION
    elif args.method == "bottleneck":
        distmeth = diagram_distance.DistMethod.BOTTLENECK
    elif args.method == "lexico":
        distmeth = diagram_distance.DistMethod.LEXICO

    res = {}
    for ds in sorted(glob.glob("diagrams/*_expl_Dipha.dipha")):
        res[ds.split("/")[-1]] = diagram_distance.main(
            ds, args.pers_threshold, distmeth, args.timeout, False
        )

        with open("distances.json", "w") as dst:
            json.dump(res, dst, indent=4)

    return res


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
    )
    prep_datasets.add_argument(
        "-3",
        "--only_cubes",
        help="Only generate 3D cubes",
        action="store_true",
    )
    prep_datasets.add_argument(
        "-2",
        "--only_slices",
        help="Only generate 2D slices",
        action="store_true",
    )
    prep_datasets.add_argument(
        "-1",
        "--only_lines",
        help="Only generate 1D lines",
        action="store_true",
    )
    prep_datasets.set_defaults(func=prepare_datasets)

    get_diags = subparsers.add_parser("compute_diagrams")
    get_diags.add_argument(
        "-s",
        "--sequential",
        help="Disable the multi-threading support",
        action="store_true",
    )
    get_diags.add_argument(
        "-t",
        "--timeout",
        help="Timeout in seconds of every persistence diagram computation",
        type=int,
        default=TIMEOUT_S,
    )
    get_diags.add_argument(
        "-3",
        "--only_cubes",
        help="Only process 3D datasets",
        action="store_true",
    )
    get_diags.add_argument(
        "-2",
        "--only_slices",
        help="Only process 2D datasets",
        action="store_true",
    )
    get_diags.add_argument(
        "-1",
        "--only_lines",
        help="Only process 1D datasets",
        action="store_true",
    )
    get_diags.add_argument(
        "-r",
        "--resume",
        help="Resume computation from given file",
    )
    get_diags.set_defaults(func=compute_diagrams)

    get_dists = subparsers.add_parser("compute_distances")
    get_dists.set_defaults(func=compute_distances)
    get_dists.add_argument(
        "-m",
        "--method",
        help="Comparison method",
        choices=["auction", "bottleneck", "lexico"],
        default="lexico",
    )
    get_dists.add_argument(
        "-p",
        "--pers_threshold",
        type=float,
        help="Threshold persistence below value before computing distance",
        default=0.0,
    )
    get_dists.add_argument(
        "-t",
        "--timeout",
        help="Timeout in seconds of every persistence diagram computation",
        type=int,
        default=TIMEOUT_S,
    )

    cli_args = parser.parse_args()

    # force use of subcommand, display help without one
    if "func" in cli_args.__dict__:
        cli_args.func(cli_args)
    else:
        parser.parse_args(["--help"])


def set_env_and_run():
    import sysconfig

    env = dict(os.environ)
    prefix = f"{os.getcwd()}/build_dirs/install_paraview_v5.10.1"
    env["PV_PLUGIN_PATH"] = f"{prefix}/bin/plugins"
    env["LD_LIBRARY_PATH"] = f"{prefix}/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
    env["PYTHONPATH"] = ":".join(
        [
            f"{prefix}/lib/python{sysconfig.get_python_version()}/site-packages",
            f"{prefix}/lib",
        ]
    )

    subprocess.check_call([sys.executable] + sys.argv, env=env)


if __name__ == "__main__":
    import psutil

    if psutil.Process().parent().cmdline()[1:] == sys.argv:
        main()
    else:
        set_env_and_run()

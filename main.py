#!/usr/bin/env python3

import argparse
import glob
import json
import math
import os
import re
import subprocess
import tarfile
import time

import requests
from paraview import simple

URL = "https://klacansky.com/open-scivis-datasets/data_sets.json"
SIZE_LIMIT_MB = 80


def get_datasets_urls(size_limit_mb):
    req = requests.get(URL)
    datasets_json = json.loads(req.text)

    dtype_size = {
        "uint8": 1,
        "int16": 2,
        "uint16": 2,
        "float32": 4,
        "float64": 8,
    }

    return [
        dataset["url"]
        for dataset in datasets_json
        if math.prod(dataset["size"]) * dtype_size[dataset["type"]]
        < (size_limit_mb * 1e6)
    ]


def download_dataset(dataset_url, name=None):
    dataset_name = name if name is not None else dataset_url.split("/")[-1]
    # https://stackoverflow.com/questions/16694907/download-large-file-in-python-with-requests
    with requests.get(dataset_url, stream=True) as req:
        with open(dataset_name, "wb") as dest:
            for chunk in req.iter_content(chunk_size=8192):
                dest.write(chunk)
    print("Downloaded " + dataset_name)


def download_datasets(datasets_urls):
    for url in datasets_urls:
        download_dataset(url)


def convert_dataset(raw_file, normalize=True):
    extent, dtype = raw_file.split(".")[0].split("_")[-2:]
    extent = [int(dim) for dim in extent.split("x")]

    dtype_pv = {
        "uint8": "unsigned char",
        "int16": "short",
        "uint16": "unsigned short",
        "float32": "float",
        "float64": "double",
    }

    raw = simple.ImageReader(FileNames=[raw_file])
    raw.DataScalarType = dtype_pv[dtype]
    raw.DataExtent = [0, extent[0] - 1, 0, extent[1] - 1, 0, extent[2] - 1]
    raw_stem = raw_file.split(".")[0]
    outp = raw

    if normalize:
        # normalize scalar field
        pdc = simple.TTKPointDataConverter(Input=raw)
        pdc.PointDataScalarField = ["POINTS", "ImageFile"]
        pdc.OutputType = "Float"
        sfnorm = simple.TTKScalarFieldNormalizer(Input=pdc)
        sfnorm.ScalarField = ["POINTS", "ImageFile"]
        outp = sfnorm

    # vtkImageData (TTK)
    simple.SaveData(
        raw_stem + ".vti",
        proxy=outp,
        PointDataArrays=["ImageFile"],
    )
    # Dipha Image Data (Dipha, CubicalRipser)
    simple.SaveData(
        raw_stem + ".dipha",
        proxy=outp,
    )
    # Perseus Cubical Grid (Gudhi)
    simple.SaveData(
        raw_stem + ".pers",
        proxy=outp,
    )

    print("Converted " + raw_file + " to VTI, Dipha and Perseus")


def prepare_datasets(_, size_limit=SIZE_LIMIT_MB):
    datasets_urls = get_datasets_urls(size_limit)
    download_datasets(datasets_urls)
    for dataset in datasets_urls:
        convert_dataset(dataset.split("/")[-1])


def download_and_build_software(_):
    gh = "https://github.com"
    tb = "tarball"
    gudhi_url = f"{gh}/GUDHI/gudhi-devel/{tb}/tags%2Fgudhi-release-3.3.0"
    CubicalRipser_url = f"{gh}/CubicalRipser/CubicalRipser_3dim/{tb}/master"
    dipha_url = f"{gh}/DIPHA/dipha/{tb}/master"

    softs = ["dipha", "gudhi", "CubicalRipser"]

    # download and extract a tarball from GitHub
    for soft in softs:
        download_dataset(locals()[soft + "_url"], soft + ".tar.gz")
        with tarfile.open(soft + ".tar.gz", "r:gz") as src:
            src.extractall()
            # rename software folders
            os.rename(src.getmembers()[0].name, soft)
        print("Extracted " + soft + " archive")

    # build the 3 applications
    subprocess.check_call(["make", "-C", "CubicalRipser"])

    for cmake_soft in ["dipha", "gudhi"]:
        builddir = "build_" + cmake_soft
        try:
            os.mkdir(builddir)
        except FileExistsError:
            pass
        subprocess.check_call("cmake", "-S", cmake_soft, "-B", builddir)
        subprocess.check_call("cmake", "--build", builddir)


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

    for exe in exes.values():
        if not os.path.isfile(exe):
            print(exe + " not found")

    try:
        os.mkdir("diagrams")
    except FileExistsError:
        pass

    times = dict()

    for inp in sorted(glob.glob("*.vti")):
        exe = exes["ttk"]
        dataset = inp.split(".")[0]
        times[dataset] = dict()
        print("Processing " + dataset + " with TTK...")
        outp = f"diagrams/{dataset}.vtu"
        cmd = [exe, "-i", inp]
        start_time = time.time()
        subprocess.check_call(cmd)
        times[dataset]["ttk"] = time.time() - start_time
        os.rename("output_port_0.vtu", outp)

    for inp in sorted(glob.glob("*.dipha")):
        exe = exes["dipha"]
        dataset = inp.split(".")[0]
        print("Processing " + dataset + " with dipha...")
        outp = f"diagrams/{dataset}.dipha"
        cmd = [
            "mpirun",
            "--use-hwthread-cpus",
            exe,
            "--benchmark",
            "--upper_dim",
            str(3),
            inp,
            outp,
        ]
        start_time = time.time()
        subprocess.run(cmd, capture_output=True)
        times[dataset]["dipha"] = time.time() - start_time

    if all_softs:
        for inp in sorted(glob.glob("*.dipha")):
            exe = exes["CubicalRipser"]
            dataset = inp.split(".")[0]
            if "float" in dataset:
                # skip large datasets
                continue
            print("Processing " + dataset + " with CubicalRipser...")
            outp = f"diagrams/{dataset}.cr"
            cmd = [exe, inp, "--output", outp]
            try:
                start_time = time.time()
                subprocess.check_call(cmd)
                times[dataset]["CubicalRipser"] = time.time() - start_time
            except subprocess.CalledProcessError:
                print(dataset + " is too large for CubicalRipser")

        for inp in sorted(glob.glob("*.pers")):
            exe = exes["gudhi"]
            dataset = inp.split(".")[0]
            print("Processing " + dataset + " with Gudhi...")
            outp = f"diagrams/{dataset}.gudhi"
            cmd = [exe, inp]
            start_time = time.time()
            subprocess.check_call(cmd)
            times[dataset]["gudhi"] = time.time() - start_time
            os.rename(inp + "_persistence", outp)

    with open("results", "w") as dst:
        dst.write(json.dumps(times))
    return times


def compute_distances(_, method="auction"):
    # list of datasets that have at least one persistence diagram
    datasets = sorted(set(f.split(".")[0] for f in glob.glob("diagrams/*")))

    float_re = r"(\d+\.\d+|\d+)"
    auct_patt = re.compile(
        rf"[Min-saddle|Saddle-saddle|Saddle-max] cost\s+:\s+{float_re}"
    )
    btnk_patt = re.compile(
        rf"diagMax\({float_re}\), diagMin\({float_re}\), diagSad\({float_re}\)"
    )
    dists = dict()

    for ds in datasets:
        ttk_diag = ds + ".vtu"
        dipha_diag = ds + ".dipha"
        empty_diag = "empty.vtu"

        if os.path.isfile(ttk_diag) and os.path.isfile(dipha_diag):
            cmd = ["python", "ttk_distance.py", method, dipha_diag, ttk_diag]
            print(f"Computing distance between TTK and Dipha diagrams for {ds}")
            proc0 = subprocess.run(cmd, capture_output=True)
            cmd = ["python", "ttk_distance.py", method, dipha_diag, empty_diag]
            print(f"Computing Dipha distance to empty diagram for {ds}")
            proc1 = subprocess.run(cmd, capture_output=True)
            if method == "auction":
                matches0 = re.findall(auct_patt, str(proc0.stdout))
                matches1 = re.findall(auct_patt, str(proc1.stdout))

            elif method == "bottleneck":
                matches0 = re.findall(btnk_patt, str(proc0.stdout))[0]
                matches1 = re.findall(btnk_patt, str(proc1.stdout))[0]

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

    dl_softs = subparsers.add_parser("download_software")
    dl_softs.set_defaults(func=download_and_build_software)

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

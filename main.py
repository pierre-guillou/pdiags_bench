#!/usr/bin/env python3

import argparse
import glob
import json
import math
import os
import subprocess
import tarfile
import time

import requests
from paraview import simple

URL = "https://klacansky.com/open-scivis-datasets/data_sets.json"
SIZE_LIMIT_MB = 100


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


def convert_dataset(raw_file):
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
    # vtkImageData (TTK)
    simple.SaveData(
        raw_stem + ".vti",
        proxy=raw,
        PointDataArrays=["ImageFile"],
    )
    # Dipha Image Data (Dipha, CubicalRipser)
    simple.SaveData(
        raw_stem + ".dipha",
        proxy=raw,
    )
    # Perseus Cubical Grid (Gudhi)
    simple.SaveData(
        raw_stem + ".pers",
        proxy=raw,
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


def compute_diagrams(_):
    exes = {
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
    for raw in glob.glob("*.raw"):
        dataset = raw.split(".")[0]
        times[dataset] = dict()

    for inp in glob.glob("*.vti"):
        dataset = inp.split(".")[0]
        outp = f"diagrams/{dataset}.vtu"
        data = simple.XMLImageDataReader(FileName=[inp])
        pdiag = simple.TTKPersistenceDiagram(Input=data)
        pdiag.ScalarField = ["POINTS", "ImageFile"]
        pdiag.InputOffsetField = ["POINTS", "ImageFile"]
        pdiag.ComputepairswiththeDiscreteGradient = True
        start_time = time.time()
        simple.SaveData(outp, Input=pdiag)
        times[dataset]["ttk"] = time.time() - start_time
        print("Processed " + dataset + " with TTK")

    for inp in glob.glob("*.dipha"):
        exe = exes["dipha"]
        dataset = inp.split(".")[0]
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
        print("Processed " + dataset + " with dipha")

    for inp in glob.glob("*.dipha"):
        exe = exes["CubicalRipser"]
        dataset = inp.split(".")[0]
        outp = f"diagrams/{dataset}.cr"
        cmd = [exe, inp, "--output", outp]
        try:
            start_time = time.time()
            subprocess.check_call(cmd)
            times[dataset]["CubicalRipser"] = time.time() - start_time
            print("Processed " + dataset + " with CubicalRipser")
        except subprocess.CalledProcessError:
            print(dataset + " is too large for CubicalRipser")

    for inp in glob.glob("*.pers"):
        exe = exes["gudhi"]
        dataset = inp.split(".")[0]
        outp = f"diagrams/{dataset}.gudhi"
        cmd = [exe, inp]
        start_time = time.time()
        subprocess.check_call(cmd)
        times[dataset]["gudhi"] = time.time() - start_time
        os.rename(inp + "_persistence", outp)
        print("Processed " + dataset + " with Gudhi")

    with open("results", "w") as dst:
        dst.write(json.dumps(times))
    return times


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

    cli_args = parser.parse_args()

    # force use of subcommand, display help without one
    if "func" in cli_args.__dict__:
        cli_args.func(cli_args)
    else:
        parser.parse_args(["--help"])


if __name__ == "__main__":
    main()

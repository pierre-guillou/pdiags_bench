#!/usr/bin/env python3

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
SIZE_LIMIT_MB = 10


def get_datasets_urls():
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
        < (SIZE_LIMIT_MB * 1e6)
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


def convert_datasets(raw_file):
    extent, dtype = raw_file.split(".")[0].split("_")[-2:]
    extent = [int(dim) for dim in extent.split("x")]

    dtype_pv = {
        "uint8": "unsigned char",
        "int16": "signed short",
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


def download_software():
    gh = "https://github.com"
    tb = "tarball"
    gudhi_url = f"{gh}/GUDHI/gudhi-devel/{tb}/tags%2Fgudhi-release-3.3.0"
    CubicalRipser_url = f"{gh}/CubicalRipser/CubicalRipser_3dim/{tb}/master"
    dipha_url = f"{gh}/DIPHA/dipha/{tb}/master"

    softs = ["dipha", "gudhi", "CubicalRipser"]

    for soft in softs:
        download_dataset(locals()[soft + "_url"], soft + ".tar.gz")
        with tarfile.open(soft + ".tar.gz", "r:gz") as src:
            src.extractall()
            # rename software folders
            os.rename(src.getmembers()[0].name, soft)
        print("Extracted " + soft + " archive")

    return softs


def build_software():
    os.system("make -C CubicalRipser")

    for cmake_soft in ["dipha", "gudhi"]:
        builddir = "build_" + cmake_soft
        try:
            os.mkdir(builddir)
        except FileExistsError:
            pass
        os.system("cmake -S " + cmake_soft + " -B " + builddir)
        os.system("cmake --build " + builddir)


def compute_diagrams(nThreads=4):
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
        pdiag.ThreadNumber = nThreads
        start_time = time.time()
        simple.SaveData(outp, simple.CleantoGrid(Input=pdiag))
        times[dataset]["ttk"] = time.time() - start_time

    for inp in glob.glob("*.dipha"):
        exe = exes["dipha"]
        dataset = inp.split(".")[0]
        outp = f"diagrams/{dataset}.dipha"
        cmd = [
            "mpirun",
            "-np",
            str(nThreads),
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

    for inp in glob.glob("*.dipha"):
        exe = exes["CubicalRipser"]
        dataset = inp.split(".")[0]
        outp = f"diagrams/{dataset}.cr"
        cmd = [exe, inp, "--output", outp]
        start_time = time.time()
        subprocess.check_call(cmd)
        times[dataset]["CubicalRipser"] = time.time() - start_time

    for inp in glob.glob("*.pers"):
        exe = exes["gudhi"]
        dataset = inp.split(".")[0]
        outp = f"diagrams/{dataset}.gudhi"
        cmd = [exe, inp]
        start_time = time.time()
        subprocess.check_call(cmd)
        times[dataset]["gudhi"] = time.time() - start_time
        os.rename(inp + "_persistence", outp)

    with open("results", "w") as dst:
        dst.write(json.dumps(times))
    return times


def main():
    # datasets_urls = get_datasets_urls()
    # download_datasets(datasets_urls)
    # for dataset in glob.glob("*.raw"):
    #     convert_datasets(dataset)
    # download_software()
    # build_software()
    compute_diagrams()


if __name__ == "__main__":
    main()

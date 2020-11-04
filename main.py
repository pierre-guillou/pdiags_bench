import glob
import json
import math
import tarfile

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
    extent, dtype = raw_file.split("_")[-2:]
    extent = [int(dim) for dim in extent.split("x")]

    def get_dtype(dtype):
        if dtype == "uint8":
            return "unsigned char"
        elif dtype == "int16":
            return "signed short"
        elif dtype == "uint16":
            return "unsigned short"
        elif dtype == "float32":
            return "float"
        elif dtype == "float64":
            return "double"

    dtype = get_dtype(dtype.split(".")[0])

    raw = simple.ImageReader(FileNames=[raw_file])
    raw.DataScalarType = dtype
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
    cubicalRipser_url = f"{gh}/CubicalRipser/CubicalRipser_3dim/{tb}/master"
    dipha_url = f"{gh}/DIPHA/dipha/{tb}/master"

    download_dataset(dipha_url, "dipha.tar.gz")
    download_dataset(gudhi_url, "gudhi.tar.gz")
    download_dataset(cubicalRipser_url, "CubicalRipser.tar.gz")

    for soft in ["dipha", "gudhi", "CubicalRipser"]:
        with tarfile.open(soft + ".tar.gz", "r:gz") as src:
            src.extractall()


def main():
    # datasets_urls = get_datasets_urls()
    # download_datasets(datasets_urls)
    # for dataset in glob.glob("*.raw"):
    #     convert_datasets(dataset)
    download_software()


if __name__ == "__main__":
    main()

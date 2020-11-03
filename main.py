import glob
import json
import math

import requests
from paraview import simple

URL = "https://klacansky.com/open-scivis-datasets/data_sets.json"
SIZE_LIMIT = 128 ** 3


def get_datasets_urls():
    req = requests.get(URL)
    datasets_json = json.loads(req.text)
    return [
        dataset["url"]
        for dataset in datasets_json
        if math.prod(dataset["size"]) < SIZE_LIMIT
    ]


def download_dataset(dataset_url):
    dataset_name = dataset_url.split("/")[-1]
    # https://stackoverflow.com/questions/16694907/download-large-file-in-python-with-requests
    with requests.get(dataset_url, stream=True) as req:
        with open(dataset_name, "wb") as dest:
            for chunk in req.iter_content(chunk_size=8192):
                dest.write(chunk)
    print("Downloaded " + dataset_name)


def download_datasets(datasets_urls):
    for url in datasets_urls:
        download_dataset(url)


def convert_to_vti(raw_file):
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
    simple.SaveData(
        raw_file.split(".")[0] + ".vti",
        proxy=raw,
        PointDataArrays=["ImageFile"],
    )
    print("Converted " + raw_file + " to VTI")


def main():
    # datasets_urls = get_datasets_urls()
    # download_datasets(datasets_urls)
    for dataset in glob.glob("*.raw"):
        convert_to_vti(dataset)


if __name__ == "__main__":
    main()

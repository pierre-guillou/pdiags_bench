import glob
import json
import math
import os

import requests

URL = "https://klacansky.com/open-scivis-datasets/datasets.json"
SIZE_LIMIT_MB = 1024


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
        for dataset in datasets_json.values()
        if math.prod(dataset["size"]) * dtype_size[dataset["type"]]
        < (size_limit_mb * 1e6)
    ]


def download_file(url, dest):
    # https://stackoverflow.com/questions/16694907/download-large-file-in-python-with-requests
    with requests.get(url, stream=True) as req:
        with open(dest, "wb") as dst:
            for chunk in req.iter_content(chunk_size=8192):
                dst.write(chunk)
    print(f"Downloaded {dest} from {url}")


def download_dataset(dataset_url, dest_dir=""):
    dataset_name = dataset_url.split("/")[-1]
    if dest_dir + dataset_name in glob.glob(dest_dir + "*.raw"):
        print(f"{dataset_name} already downloaded, skipping...")
        return
    download_file(dataset_url, dest_dir + dataset_name)


def main(max_size=SIZE_LIMIT_MB):
    dest_dir = "raws"
    try:
        os.mkdir(dest_dir)
    except FileExistsError:
        pass

    ds_urls = get_datasets_urls(max_size)
    for url in ds_urls:
        download_dataset(url, dest_dir + "/")


if __name__ == "__main__":
    main()

import json
import math

import requests

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


def main():
    datasets_urls = get_datasets_urls()
    download_datasets(datasets_urls)


if __name__ == "__main__":
    main()

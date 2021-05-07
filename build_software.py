import os
import subprocess
import zipfile

from download_datasets import download_file


def create_dir(dirname):
    try:
        os.mkdir(dirname)
    except FileExistsError:
        pass


PERSEUS_URL = "https://people.maths.ox.ac.uk/nanda/source/perseus_4_beta.zip"


def download_perseus(perseus_url=PERSEUS_URL):
    # download Perseus from project server
    perseus_zip = perseus_url.split("/")[-1]
    download_file(perseus_url, perseus_zip)
    create_dir("perseus")
    with zipfile.ZipFile(perseus_zip, "r") as src:
        src.extractall("perseus")
    # remove zip
    os.remove(perseus_zip)


def main():

    softs = [
        "CubicalRipser",
        "diamorse",
        "dipha",
        "oineus",
        "perseus",
    ]

    # 1. Fetch submodules
    subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True)

    # 2. Build each library
    for soft in softs:
        if soft == "CubicalRipser":
            # build CubicalRipser
            subprocess.run(["make"], cwd=soft, check=True)
        elif soft == "perseus":
            # download Perseus
            download_perseus()
            # build perseus
            subprocess.run(
                ["g++", "Pers.cpp", "-O3", "-fpermissive", "-o", "perseus"],
                cwd=soft,
                check=True,
            )
        elif soft == "diamorse":
            # build diamorse
            try:
                subprocess.run(
                    [
                        "sed",
                        "s/shell python/shell python2/",
                        "-i",
                        "src/python/Makefile",
                    ],
                    cwd=soft,
                    check=True,
                )
                subprocess.run(["make", "all"], cwd=soft, check=True)
            except subprocess.CalledProcessError:
                print("Missing cython, python2-numpy to build diamorse")
        else:
            builddir = "build_" + soft
            create_dir(builddir)
            subprocess.check_call(["cmake", "-S", soft, "-B", builddir])
            subprocess.check_call(["cmake", "--build", builddir])

    # 3. Try poetry install
    try:
        subprocess.run(["poetry", "install"], check=True)
    except FileNotFoundError:
        print(
            "This software needs Poetry (https://python-poetry.org/)"
            " to manage the Python dependencies"
        )


if __name__ == "__main__":
    main()

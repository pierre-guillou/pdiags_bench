import os
import shutil
import subprocess
import zipfile

from download_datasets import download_file


def create_dir(dirname):
    try:
        os.mkdir(dirname)
    except FileExistsError:
        pass


def dl_build_perseus(perseus_url):
    # download Perseus from project server
    perseus_zip = perseus_url.split("/")[-1]
    download_file(perseus_url, perseus_zip)
    create_dir("perseus")
    with zipfile.ZipFile(perseus_zip, "r") as src:
        src.extractall("perseus")
    # build perseus
    subprocess.check_call(
        ["g++", "Pers.cpp", "-O3", "-fpermissive", "-o", "perseus"], cwd="perseus"
    )
    # remove zip
    os.remove(perseus_zip)


def main():
    gh = "https://github.com"

    softs = {
        "dipha": f"{gh}/DIPHA/dipha",
        "CubicalRipser": f"{gh}/CubicalRipser/CubicalRipser_3dim",
        "perseus": "https://people.maths.ox.ac.uk/nanda/source/perseus_4_beta.zip",
        "oineus": f"{gh}/grey-narn/oineus",
    }

    # download and extract a tarball from GitHub
    for soft, url in softs.items():
        if soft == "perseus":
            continue
        try:
            subprocess.check_call(["git", "clone", url, "--depth", "1", soft])
            subprocess.check_call(["git", "submodule", "update", "--init"], cwd=soft)
            print(f"Cloned {soft} repository")
        except subprocess.CalledProcessError:
            print(f"Repository {soft} already cloned")

    # build the applications
    for soft, _ in softs.items():
        if soft == "CubicalRipser":
            subprocess.check_call(["make", "-C", "CubicalRipser"])
        elif soft == "perseus":
            # download & build Perseus
            dl_build_perseus(softs["perseus"])
        else:
            builddir = "build_" + soft
            create_dir(builddir)
            subprocess.check_call(["cmake", "-S", soft, "-B", builddir])
            subprocess.check_call(["cmake", "--build", builddir])
            # remove source directory/git repository?
            shutil.rmtree(soft)


if __name__ == "__main__":
    main()

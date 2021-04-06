import os
import subprocess
import tarfile
import zipfile

from download_datasets import download_dataset


def create_dir(dirname):
    try:
        os.mkdir(dirname)
    except FileExistsError:
        pass


def dl_build_perseus(perseus_url):
    # download Perseus from project server
    perseus_zip = perseus_url.split("/")[-1]
    download_dataset(perseus_url)
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
    tb = "tarball"
    gudhi_url = f"{gh}/GUDHI/gudhi-devel/{tb}/tags%2Fgudhi-release-3.3.0"
    CubicalRipser_url = f"{gh}/CubicalRipser/CubicalRipser_3dim/{tb}/master"
    dipha_url = f"{gh}/DIPHA/dipha/{tb}/master"
    perseus_url = "https://people.maths.ox.ac.uk/nanda/source/perseus_4_beta.zip"

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
        create_dir(builddir)
        subprocess.check_call("cmake", "-S", cmake_soft, "-B", builddir)
        subprocess.check_call("cmake", "--build", builddir)

    # download & build Perseus
    dl_build_perseus(perseus_url)


if __name__ == "__main__":
    main()

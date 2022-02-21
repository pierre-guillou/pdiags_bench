import os
import shutil
import subprocess
import time
import zipfile

from download_datasets import download_file


def create_dir(dirname):
    try:
        os.mkdir(dirname)
    except FileExistsError:
        pass


PERSEUS_URL = "https://people.maths.ox.ac.uk/nanda/source/perseus_4_beta.zip"
JAVAPLEX_URL = (
    "https://github.com/appliedtopology/javaplex"
    "/files/2196392/javaplex-processing-lib-4.3.4.zip"
)


def download_perseus(perseus_url=PERSEUS_URL):
    # download Perseus from project server
    perseus_zip = perseus_url.split("/")[-1]
    download_file(perseus_url, perseus_zip)
    create_dir("perseus")
    with zipfile.ZipFile(perseus_zip, "r") as src:
        src.extractall("perseus")
    # remove zip
    os.remove(perseus_zip)


def download_javaplex(jplex_url=JAVAPLEX_URL):
    # download JAR from GitHub repository latest release
    jplex_zip = jplex_url.split("/")[-1]
    download_file(jplex_url, jplex_zip)
    create_dir("javaplex")
    with zipfile.ZipFile(jplex_zip, "r") as src:
        src.extract("javaplex/library/javaplex.jar")
    # move JAR to cwd
    os.replace("javaplex/library/javaplex.jar", "javaplex.jar")
    os.removedirs("javaplex/library")
    # remove zip
    os.remove(jplex_zip)


def main():

    softs = [
        "CubicalRipser_2dim",
        "CubicalRipser_3dim",
        "diamorse",
        "dipha",
        "Eirene.jl",
        "gudhi",
        "oineus",
        "perseus",
        "JavaPlex",
        "phat",
    ]

    # 1. Fetch submodules
    subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True)

    # 2. Build each library
    for soft in softs:
        print(f"Building {soft}...")
        start = time.time()
        builddir = f"build_{soft}"
        if "CubicalRipser" in soft:
            # build CubicalRipser
            subprocess.run(["make"], cwd=soft, check=True)
        elif soft == "perseus":
            # download Perseus
            download_perseus()
            # build perseus
            try:
                shutil.copy2("patches/Makefile.perseus", f"{soft}/Makefile")
            except shutil.SameFileError:
                pass
            subprocess.run(["make"], cwd=soft, check=True)
        elif soft == "diamorse":
            # build diamorse
            try:
                subprocess.run(
                    ["git", "checkout", "."],
                    cwd=soft,
                    check=True,
                )
                subprocess.run(
                    ["git", "apply", "../patches/diamorse_*.patch"],
                    cwd=soft,
                    check=True,
                )
                subprocess.run(["make", "all"], cwd=soft, check=True)
            except subprocess.CalledProcessError:
                print("Missing cython, python2-numpy to build diamorse")
        elif soft == "Eirene.jl":
            subprocess.run(["julia", "-e", 'using Pkg; Pkg.add("Eirene")'], check=True)
        elif soft == "JavaPlex":
            download_javaplex()
            subprocess.run(
                ["javac", "-classpath", "javaplex.jar", "jplex_persistence.java"],
                check=True,
            )
        elif soft == "gudhi":
            create_dir(builddir)
            subprocess.check_call(
                ["cmake"]
                + ["-DWITH_GUDHI_TEST=OFF", "-DWITH_GUDHI_UTILITIES=OFF"]
                + ["-S", soft]
                + ["-B", builddir]
            )
            subprocess.check_call(["cmake", "--build", builddir])
        else:
            create_dir(builddir)
            subprocess.check_call(["cmake", "-S", soft, "-B", builddir])
            subprocess.check_call(["cmake", "--build", builddir])

        end = time.time()
        print(f"Built {soft} in {end - start:.3f}\n")

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

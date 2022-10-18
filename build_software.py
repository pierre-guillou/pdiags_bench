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
        src.extractall("backends_src/perseus")
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
    os.replace("javaplex/library/javaplex.jar", "backends_src/javaplex.jar")
    os.removedirs("javaplex/library")
    # remove zip
    os.remove(jplex_zip)


def clean_env():
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("LD_LIBRARY_PATH", None)
    env.pop("PV_PLUGIN_PATH", None)
    env["CMAKE_PREFIX_PATH"] = ""
    return env


def build_paraview(prefix, vers, opts):
    pv = "backends_src/paraview-ttk"
    builddir = f"build_dirs/paraview_{vers}"
    create_dir(builddir)
    subprocess.run(["git", "checkout", vers], cwd=pv, check=True)
    subprocess.check_call(
        ["cmake"]
        + ["-S", pv]
        + ["-B", builddir]
        + ["-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_INSTALL_PREFIX={prefix}"]
        + opts,
        env=clean_env(),
    )
    # double configure needed here to prevent undefined reference errors
    subprocess.check_call(["cmake", builddir])
    subprocess.check_call(["cmake", "--build", builddir, "--target", "install"])


def main():

    softs = [
        "CubicalRipser_2dim",
        "CubicalRipser_3dim",
        "diamorse",
        "dipha",
        "Eirene.jl",
        "gudhi",
        "oineus",
        "ripser",
        "perseus",
        "JavaPlex",
        "phat",
        "PersistenceCycles",
        "DiscreteMorseSandwich",
    ]

    # 1. Fetch submodules
    subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True)
    subprocess.run(["git", "submodule", "foreach", "git", "checkout", "."], check=True)

    # 2. Build each library
    create_dir("build_dirs")
    for soft in softs:
        print(f"Building {soft}...")
        soft_src = f"backends_src/{soft}"
        start = time.time()
        builddir = f"build_dirs/{soft}"
        if "CubicalRipser" in soft:
            # build CubicalRipser
            subprocess.run(["make"], cwd=soft_src, check=True)
        elif soft == "perseus":
            # download Perseus
            download_perseus()
            # build perseus
            try:
                shutil.copy2("patches/Makefile.perseus", f"{soft_src}/Makefile")
            except shutil.SameFileError:
                pass
            subprocess.run(["make"], cwd=soft_src, check=True)
        elif soft == "diamorse":
            # build diamorse
            try:
                subprocess.run(["git", "checkout", "."], cwd=soft_src, check=True)
                subprocess.run(
                    [
                        "git",
                        "apply",
                        "../../patches/diamorse_0001-Makefile-Target-Python2.patch",
                        "../../patches/diamorse_0002-persistence.py-Add-Gudhi-format-output.patch",
                    ],
                    cwd=soft_src,
                    check=True,
                )
                subprocess.run(["make", "all"], cwd=soft_src, check=True)
            except subprocess.CalledProcessError:
                print("Missing cython, python2-numpy to build diamorse")
        elif soft == "Eirene.jl":
            subprocess.run(["julia", "-e", 'using Pkg; Pkg.add("Eirene")'], check=True)
        elif soft == "JavaPlex":
            download_javaplex()
            subprocess.run(
                [
                    "javac",
                    "-classpath",
                    "backends_src/javaplex.jar",
                    "jplex_persistence.java",
                ],
                check=True,
            )
        elif soft == "gudhi":
            create_dir(builddir)
            subprocess.check_call(
                ["cmake"]
                + [
                    "-DWITH_GUDHI_TEST=OFF",
                    "-DWITH_GUDHI_UTILITIES=OFF",
                    "-DCMAKE_BUILD_TYPE=Release",
                ]
                + ["-S", soft_src]
                + ["-B", builddir]
            )
            subprocess.check_call(["cmake", "--build", builddir])
        elif soft == "ripser":
            subprocess.run(["make"], cwd=soft_src, check=True)
        elif soft == "PersistenceCycles":
            # first build ParaView 5.6.1
            pv_ver = "v5.6.1"
            prefix = f"build_dirs/install_paraview_{pv_ver}"
            build_paraview(
                prefix,
                pv_ver,
                ["-DPARAVIEW_BUILD_QT_GUI=OFF", "-DVTK_Group_ParaViewRendering=OFF"],
            )
            # apply patch (to prevent segfaults)
            subprocess.run(["git", "checkout", "."], cwd=soft_src, check=True)
            subprocess.run(
                [
                    "git",
                    "apply",
                    "../../patches/PersistenceCycles_0001-Fix-Wreturn-type.patch",
                    "../../patches/PersistenceCycles_0003-Output-Diagram-in-Gudhi-format.patch",
                ],
                cwd=soft_src,
                check=True,
            )
            create_dir(builddir)
            env = clean_env()
            env["CMAKE_PREFIX_PATH"] = prefix
            subprocess.check_call(
                ["cmake"]
                + ["-S", f"{soft_src}/ttk-0.9.7"]
                + ["-B", builddir]
                + [
                    f"-DVTK_DIR={os.getcwd()}/{prefix}/lib/cmake/paraview-5.6",
                    "-DCMAKE_BUILD_TYPE=Release",
                    f"-DCMAKE_INSTALL_PREFIX={prefix}",
                    "-DTTK_ENABLE_KAMIKAZE=ON",
                ],
                env=env,
            )
            subprocess.check_call(["cmake", "--build", builddir, "--target", "install"])
        elif soft == "DiscreteMorseSandwich":
            # first build ParaView 5.10.1
            pv_ver = "v5.10.1"
            prefix = f"build_dirs/install_paraview_{pv_ver}"
            build_paraview(
                prefix,
                pv_ver,
                ["-DPARAVIEW_USE_QT=OFF", "-DVTK_Group_ENABLE_Rendering=NO"],
            )
            # apply DiscreteMorseSandwich patch
            subprocess.run(
                [
                    "git",
                    "apply",
                    "../../patches/DiscreteMorseSandwich_filters.patch",
                ],
                cwd=soft_src,
                check=True,
            )
            # prep env variable
            create_dir(builddir)
            env = clean_env()
            env["CMAKE_PREFIX_PATH"] = prefix
            # configure TTK build directory
            subprocess.check_call(
                ["cmake"]
                + ["-S", f"{soft_src}"]
                + ["-B", builddir]
                + [
                    f"-DVTK_DIR={os.getcwd()}/{prefix}/lib/cmake/paraview-5.10",
                    "-DCMAKE_BUILD_TYPE=Release",
                    f"-DCMAKE_INSTALL_PREFIX={prefix}",
                    "-DTTK_ENABLE_KAMIKAZE=ON",
                ],
                env=env,
            )
            # build & install TTK in ParaView install prefix
            subprocess.check_call(["cmake", "--build", builddir, "--target", "install"])
        else:
            if soft == "dipha":
                subprocess.run(
                    [
                        "git",
                        "apply",
                        "../../patches/Dipha_0001-Print-sum-of-ranks-memory-peaks.patch",
                    ],
                    cwd=soft_src,
                    check=True,
                )
            elif soft == "oineus":
                subprocess.run(
                    [
                        "git",
                        "apply",
                        "../../patches/oineus_0001-New-example-file-for-simplicial-complexes.patch",
                    ],
                    cwd=soft_src,
                    check=True,
                )
            create_dir(builddir)
            subprocess.check_call(
                ["cmake", "-S", soft_src, "-B", builddir, "-DCMAKE_BUILD_TYPE=Release"]
            )
            subprocess.check_call(["cmake", "--build", builddir])

        end = time.time()
        print(f"Built {soft} in {int(end - start)} seconds\n")


if __name__ == "__main__":
    main()

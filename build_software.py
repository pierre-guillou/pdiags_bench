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


def clean_env():
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("LD_LIBRARY_PATH", None)
    env.pop("PV_PLUGIN_PATH", None)
    env["CMAKE_PREFIX_PATH"] = ""
    return env


def build_paraview(vers, opts):
    pv = "paraview-ttk"
    builddir = f"build_dirs/build_{pv}_{vers}"
    create_dir(builddir)
    subprocess.run(["git", "checkout", vers], cwd=pv, check=True)
    subprocess.check_call(
        [
            "cmake",
            "-S",
            pv,
            "-B",
            builddir,
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_INSTALL_PREFIX={builddir}/../install_{vers}",
        ]
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
        "perseus",
        "JavaPlex",
        "phat",
        "PersistenceCycles",
        "AlexanderSandwich",
    ]

    # 1. Fetch submodules
    subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True)

    # 2. Build each library
    create_dir("build_dirs")
    for soft in softs:
        print(f"Building {soft}...")
        start = time.time()
        builddir = f"build_dirs/build_{soft}"
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
                subprocess.run(["git", "checkout", "."], cwd=soft, check=True)
                subprocess.run(
                    [
                        "git",
                        "apply",
                        "../patches/diamorse_0001-Makefile-Target-Python2.patch",
                        "../patches/diamorse_0002-persistence.py-Add-Gudhi-format-output.patch",
                    ],
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
                + [
                    "-DWITH_GUDHI_TEST=OFF",
                    "-DWITH_GUDHI_UTILITIES=OFF",
                    "-DCMAKE_BUILD_TYPE=Release",
                ]
                + ["-S", soft]
                + ["-B", builddir]
            )
            subprocess.check_call(["cmake", "--build", builddir])
        elif soft == "PersistenceCycles":
            # first build ParaView 5.6.1
            pv_ver = "v5.6.1"
            build_paraview(
                pv_ver,
                ["-DPARAVIEW_BUILD_QT_GUI=OFF", "-DVTK_Group_ParaViewRendering=OFF"],
            )
            # apply patch (to prevent segfaults)
            subprocess.run(["git", "checkout", "."], cwd=soft, check=True)
            subprocess.run(
                [
                    "git",
                    "apply",
                    "../patches/PersistenceCycles_0001-Fix-Wreturn-type.patch",
                    "../patches/PersistenceCycles_0002-Make-Persistent-Diagram-VTU-compatible-with-TTK.patch",
                ],
                cwd=soft,
                check=True,
            )
            create_dir(builddir)
            env = clean_env()
            env["CMAKE_PREFIX_PATH"] = f"build_dirs/install_{pv_ver}"
            subprocess.check_call(
                [
                    "cmake",
                    "-S",
                    f"{soft}/ttk-0.9.7",
                    "-B",
                    builddir,
                    f"-DVTK_DIR={os.getcwd()}/build_dirs/install_{pv_ver}/lib/cmake/paraview-5.6",
                    "-DCMAKE_BUILD_TYPE=Release",
                    f"-DCMAKE_INSTALL_PREFIX={builddir}/../install_{pv_ver}",
                ],
                env=env,
            )
            subprocess.check_call(["cmake", "--build", builddir, "--target", "install"])
        elif soft == "AlexanderSandwich":
            # first build ParaView 5.10.1
            pv_ver = "v5.10.1"
            build_paraview(
                pv_ver,
                ["-DPARAVIEW_USE_QT=OFF", "-DVTK_Group_ENABLE_Rendering=NO"],
            )
            # prep env variable
            create_dir(builddir)
            env = clean_env()
            env["CMAKE_PREFIX_PATH"] = f"build_dirs/install_{pv_ver}"
            # configure TTK build directory
            subprocess.check_call(
                ["cmake"]
                + ["-S", f"{soft}"]
                + ["-B", builddir]
                + [
                    f"-DVTK_DIR={os.getcwd()}/build_dirs/install_{pv_ver}/lib/cmake/paraview-5.10",
                    "-DCMAKE_BUILD_TYPE=Release",
                    f"-DCMAKE_INSTALL_PREFIX={builddir}/../install_{pv_ver}",
                ],
                env=env,
            )
            # build & install TTK in ParaView install prefix
            subprocess.check_call(["cmake", "--build", builddir, "--target", "install"])
        else:
            create_dir(builddir)
            subprocess.check_call(
                ["cmake", "-S", soft, "-B", builddir, "-DCMAKE_BUILD_TYPE=Release"]
            )
            subprocess.check_call(["cmake", "--build", builddir])

        end = time.time()
        print(f"Built {soft} in {end - start:.3f}\n")


if __name__ == "__main__":
    main()

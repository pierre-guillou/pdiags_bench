import argparse
import multiprocessing
import os
import shutil
import subprocess
import sys
import sysconfig

import psutil


def main(input_dataset, output_diagram):
    from paraview import simple

    if "vtu" in input_dataset:
        ds = simple.XMLUnstructuredGridReader(FileName=[input_dataset])
    elif "vti" in input_dataset:
        ds = simple.XMLImageDataReader(FileName=[input_dataset])
    pd = simple.TTKFG_PersistentHomology(Input=ds)
    pd.ScalarField = "ImageFile_Order"
    simple.UpdatePipeline()
    shutil.move("/tmp/out.gudhi", output_diagram)


def set_env_and_run(thread_number):
    env = dict(os.environ)
    prefix = f"{os.getcwd()}/build_dirs/install_paraview_v5.6.1"
    env["PV_PLUGIN_PATH"] = f"{prefix}/lib/plugins"
    env["LD_LIBRARY_PATH"] = f"{prefix}/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
    env["PYTHONPATH"] = ":".join(
        [
            f"{prefix}/lib/python{sysconfig.get_python_version()}/site-packages",
            f"{prefix}/lib",
        ]
    )
    env["OMP_NUM_THREADS"] = str(thread_number)

    subprocess.check_call([sys.executable] + sys.argv, env=env)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute diagram with PersistentCycles"
    )
    parser.add_argument("input_dataset", type=str, help="Input dataset")
    parser.add_argument(
        "-o", "--output_diagram", type=str, help="Output diagram", default="out.gudhi"
    )
    parser.add_argument(
        "-t",
        "--thread_number",
        type=int,
        help="Number of threads",
        default=multiprocessing.cpu_count(),
    )
    args = parser.parse_args()

    if psutil.Process().parent().cmdline()[1:] == sys.argv:
        main(args.input_dataset, args.output_diagram)
    else:
        set_env_and_run(args.thread_number)

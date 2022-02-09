import argparse
import os
import sys
import subprocess
import sysconfig


def main(input_dataset, output_diagram):
    from paraview import simple

    ds = simple.XMLUnstructuredGridReader(FileName=[input_dataset])
    pd = simple.TTKFG_PersistentHomology(Input=ds)
    pd.ScalarField = "ImageFile_Order"
    simple.SaveData(output_diagram, proxy=pd)


def set_env_and_run(input_dataset, output_diagram):
    env = dict(os.environ)
    prefix = f"{os.getcwd()}/build_dirs/install_v5.6.1"
    env["PV_PLUGIN_PATH"] = f"{prefix}/lib/plugins"
    env["LD_LIBRARY_PATH"] = f"{prefix}/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
    env["PYTHONPATH"] = ":".join(
        [
            f"{prefix}/lib/python{sysconfig.get_python_version()}/site-packages",
            f"{prefix}/lib",
        ]
    )

    cmd = [sys.executable, __file__, input_dataset, "-o", output_diagram, "-n"]
    subprocess.check_call(cmd, env=env)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute diagram with PersistentCycles"
    )
    parser.add_argument("input_dataset", type=str, help="Input dataset")
    parser.add_argument(
        "-o", "--output_diagram", type=str, help="Output diagram", default="out.vtu"
    )
    parser.add_argument(
        "-n", "--no_set_environment", action="store_true", help="Don't set environment"
    )
    args = parser.parse_args()

    if args.no_set_environment:
        main(args.input_dataset, args.output_diagram)
    else:
        set_env_and_run(args.input_dataset, args.output_diagram)

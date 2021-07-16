import argparse
import enum
import json
import logging
import os
import pathlib
import re
import subprocess
import time

from paraview import simple

import compare_diags as cd

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)


def load_diagram(diag):
    if diag.endswith("vtu"):
        return simple.XMLUnstructuredGridReader(FileName=diag)
    if diag.endswith("dipha"):
        return simple.TTKDiphaFileFormatReader(FileName=diag)
    if diag.endswith("gudhi"):
        return simple.TTKGudhiPersistenceDiagramReader(FileName=diag)
    return None


class DistMethod(enum.Enum):
    BOTTLENECK = enum.auto()
    AUCTION = enum.auto()
    LEXICO = enum.auto()

    def __str__(self):
        return super().name.lower()


def compare_diags(args):

    diag0 = load_diagram(args.diags[0])
    diag1 = load_diagram(args.diags[1])

    if args.method == DistMethod.AUCTION:
        gd = simple.GroupDatasets(Input=[diag0, diag1])
        dist = simple.TTKPersistenceDiagramClustering(Input=gd)
        dist.Maximalcomputationtimes = 100.0
        dist.Forceminimumprecisiononmatchings = True
        dist.Minimalrelativeprecision = args.pers_threshold / 100.0

    elif args.method == DistMethod.BOTTLENECK:
        dist = simple.TTKBottleneckDistance(
            Persistencediagram1=diag0,
            Persistencediagram2=diag1,
        )
        dist.Persistencethreshold = args.pers_threshold

    simple.SaveData("dist.vtu", Input=dist)
    os.remove("dist.vtu")


def get_diag_dist(fdiag0, fdiag1, threshold_bound, method, timeout):
    float_re = r"(\d+\.\d+|\d+)"
    if method == DistMethod.AUCTION:
        pattern = re.compile(
            rf"(?:Min-saddle|Saddle-saddle|Saddle-max) cost\s+:\s+{float_re}"
        )
    elif method == DistMethod.BOTTLENECK:
        pattern = re.compile(rf"res\({float_re}\)")

    # launch compare_diags through subprocess to capture stdout
    cmd = (
        ["/usr/bin/timeout", "--preserve-status", str(timeout + 2)]
        + ["python", __file__]
        + [fdiag0, fdiag1]
        + ["-m", str(method)]
        + ["-p", str(threshold_bound)]
    )

    try:
        logging.info(
            "Computing %s distance between %s and %s...",
            method.name.lower(),
            fdiag0,
            fdiag1,
        )
        beg = time.time()
        proc = subprocess.run(cmd, capture_output=True, check=True, timeout=timeout)
        end = time.time()
        logging.info("  Done in %.3fs", end - beg)
    except subprocess.CalledProcessError:
        logging.error("  Could not compute distance")
        return None
    except subprocess.TimeoutExpired:
        logging.warning("  Timeout expired after %ds", timeout)
        return None
    matches = re.findall(pattern, str(proc.stdout))
    matches = [round(float(m), 1) for m in matches]
    pairTypes = ["min-sad", "sad-sad", "sad-max"]

    dists = dict(zip(pairTypes, matches))
    return dists


def get_file_list(diag_file):
    p = pathlib.Path(diag_file)
    if not p.exists():
        logging.error("File not found: %s", diag_file)
        return None
    stem = "_".join(p.stem.split("_")[:-1])
    l = sorted(p.parent.glob(f"{stem}*"))
    idx = next(i for i, v in enumerate(l) if "_Dipha" in str(v))
    l[0], l[idx] = l[idx], l[0]
    return l, stem


def main(diag_file, threshold, method, timeout, write_to_file=True):
    diags, stem = get_file_list(diag_file)

    dipha_diag = str(diags[0])
    res = dict()
    for diag in diags[1:]:
        if method == DistMethod.LEXICO:
            res[str(diag.name)] = cd.main(dipha_diag, str(diag), False)
        else:
            res[str(diag.name)] = get_diag_dist(
                dipha_diag, str(diag), threshold, method, timeout
            )

    if write_to_file:
        with open(f"dist_Dipha_{stem}.json", "w") as dst:
            json.dump(res, dst, indent=4)

    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Compute distance matrices between a series of persistence diagrams"
        )
    )

    parser.add_argument(
        "diags", nargs="+", help="Path to persistence diagrams to compare"
    )
    parser.add_argument(
        "-m",
        "--method",
        help="Distance Method",
        choices=["auction", "bottleneck"],
        default="auction",
    )
    parser.add_argument(
        "-p",
        "--pers_threshold",
        type=float,
        help="Threshold persistence below value before computing distance",
        default=1,
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        help="Timeout in seconds",
        default=1800,  # 30min
    )

    cli_args = parser.parse_args()

    if cli_args.method == "auction":
        cli_args.method = DistMethod.AUCTION
    elif cli_args.method == "bottleneck":
        cli_args.method = DistMethod.BOTTLENECK
    else:
        raise argparse.ArgumentError

    if len(cli_args.diags) == 1:
        main(
            cli_args.diags[0],
            cli_args.pers_threshold,
            cli_args.method,
            cli_args.timeout,
        )
    else:
        compare_diags(cli_args)

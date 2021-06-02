import argparse
import enum
import os
import re
import subprocess

from paraview import simple


def load_diagram(diag):
    if diag.endswith("vtu"):
        return simple.XMLUnstructuredGridReader(FileName=diag)
    if diag.endswith("dipha"):
        return simple.TTKDiphaFileFormatReader(FileName=diag)
    if diag.endswith("gudhi"):
        return simple.TTKGudhiPersistenceDiagramReader(FileName=diag)
    return None


class DistMethod(enum.Enum):
    BOTTLENECK = 0
    AUCTION = 1

    def __str__(self):
        return super().name.lower()


def compare_diags(fdiag0, fdiag1, method=DistMethod.AUCTION):
    diag0 = load_diagram(fdiag0)
    diag1 = load_diagram(fdiag1)
    thr_bound = 0.01

    if method == DistMethod.AUCTION:
        gd = simple.GroupDatasets(Input=[diag0, diag1])
        thr = simple.Threshold(Input=gd)
        thr.Scalars = ["CELLS", "Persistence"]
        thr.ThresholdRange = [thr_bound, 1.0]
        dist = simple.TTKPersistenceDiagramClustering(Input=thr)
        dist.Maximalcomputationtimes = 10.0

    elif method == DistMethod.BOTTLENECK:
        thr0 = simple.Threshold(Input=diag0)
        thr0.Scalars = ["CELLS", "Persistence"]
        thr0.ThresholdRange = [thr_bound, 1.0]
        thr1 = simple.Threshold(Input=diag1)
        thr1.Scalars = ["CELLS", "Persistence"]
        thr1.ThresholdRange = [thr_bound, 1.0]
        dist = simple.TTKBottleneckDistance(
            Persistencediagram1=thr0,
            Persistencediagram2=thr1,
        )

    simple.SaveData("dist.vtu", Input=dist)
    os.remove("dist.vtu")


def main(fdiag0, fdiag1, method):
    float_re = r"(\d+\.\d+|\d+)"
    if method == DistMethod.AUCTION:
        pattern = re.compile(
            rf"(?:Min-saddle|Saddle-saddle|Saddle-max) cost\s+:\s+{float_re}"
        )
    elif method == DistMethod.BOTTLENECK:
        pattern = re.compile(rf"diag(?:Max|Min|Sad)\({float_re}\)")

    # launch compare_diags through subprocess to capture stdout
    cmd = ["python", __file__, "-p", fdiag0, fdiag1, "-m", str(method)]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    matches = re.findall(pattern, str(proc.stdout))
    matches = [float(m) for m in matches]
    pairTypes = ["min-sad", "sad-sad", "sad-max"]

    dists = dict(zip(pairTypes, matches))
    print(dists)
    return dists


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Compute the Bottleneck or Auction distance "
            "between two persistence diagrams"
        )
    )
    parser.add_argument("diag0", help="Path to first input persistence diagram")
    parser.add_argument("diag1", help="Path to second input persistence diagram")
    parser.add_argument(
        "-m",
        "--method",
        help="Comparison method",
        choices=["auction", "bottleneck"],
        default="auction",
    )
    parser.add_argument(
        "-p",
        "--pipeline",
        action="store_true",
        help="Execute only the ParaView pipeline",
    )

    args = parser.parse_args()
    if args.method == "auction":
        distmeth = DistMethod.AUCTION
    elif args.method == "bottleneck":
        distmeth = DistMethod.BOTTLENECK
    else:
        raise argparse.ArgumentError

    if args.pipeline:
        compare_diags(args.diag0, args.diag1, distmeth)
    else:
        main(args.diag0, args.diag1, distmeth)

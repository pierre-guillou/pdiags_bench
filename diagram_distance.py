import argparse
import enum
import os
import pathlib
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
    BOTTLENECK = enum.auto()
    AUCTION = enum.auto()

    def __str__(self):
        return super().name.lower()


def compare_diags(fdiag0, fdiag1, thr_bound, method=DistMethod.AUCTION):
    diag0 = load_diagram(fdiag0)
    diag1 = load_diagram(fdiag1)

    if method == DistMethod.AUCTION:
        gd = simple.GroupDatasets(Input=[diag0, diag1])
        thrange = gd.GetCellDataInformation()["Persistence"].GetComponentRange(0)
        thr = simple.Threshold(Input=gd)
        thr.Scalars = ["CELLS", "Persistence"]
        thr.ThresholdRange = [thr_bound * thrange[1], thrange[1]]
        dist = simple.TTKPersistenceDiagramClustering(Input=thr)
        dist.Maximalcomputationtimes = 10.0

    elif method == DistMethod.BOTTLENECK:
        thr0range = diag0.GetCellDataInformation()["Persistence"].GetComponentRange(0)
        thr0 = simple.Threshold(Input=diag0)
        thr0.Scalars = ["CELLS", "Persistence"]
        thr0.ThresholdRange = [thr_bound * thr0range[1], thr0range[1]]
        thr1range = diag1.GetCellDataInformation()["Persistence"].GetComponentRange(0)
        thr1 = simple.Threshold(Input=diag1)
        thr1.Scalars = ["CELLS", "Persistence"]
        thr1.ThresholdRange = [thr_bound * thr1range[1], thr1range[1]]
        dist = simple.TTKBottleneckDistance(
            Persistencediagram1=thr0,
            Persistencediagram2=thr1,
        )

    simple.SaveData("dist.vtu", Input=dist)
    os.remove("dist.vtu")


def entry_point(fdiag0, fdiag1, threshold_bound, method):
    float_re = r"(\d+\.\d+|\d+)"
    if method == DistMethod.AUCTION:
        pattern = re.compile(
            rf"(?:Min-saddle|Saddle-saddle|Saddle-max) cost\s+:\s+{float_re}"
        )
    elif method == DistMethod.BOTTLENECK:
        pattern = re.compile(rf"diag(?:Max|Min|Sad)\({float_re}\)")

    # launch compare_diags through subprocess to capture stdout
    cmd = (
        ["python", __file__]
        + ["-p", fdiag0, fdiag1]
        + ["-m", str(method)]
        + ["-t", str(threshold_bound)]
    )

    proc = subprocess.run(cmd, capture_output=True, check=True)
    matches = re.findall(pattern, str(proc.stdout))
    matches = [float(m) for m in matches]
    pairTypes = ["min-sad", "sad-sad", "sad-max"]

    dists = dict(zip(pairTypes, matches))
    print(dists)
    return dists


def main(diag_file):
    p = pathlib.Path(diag_file)
    if not p.exists():
        print(f"Error: {diag_file} not found")
        return
    stem = "_".join(p.stem.split("_")[:-1])
    l = sorted(p.parent.glob(f"{stem}*"))
    diags = {d.name: load_diagram(str(d)) for d in l}

    arred = list()
    for n, d in diags.items():
        ae = simple.TTKArrayEditor(Target=d)
        ae.TargetAttributeType = "Field Data"
        ae.DataString = f"Name,{n}"
        arred.append(ae)

    gd = simple.GroupDatasets(Input=arred)

    thr = simple.Threshold(Input=gd)
    thr.Scalars = ["CELLS", "IsFinite"]
    thr.ThresholdRange = [1.0, 1.0]

    pairsType = ["min-saddle pairs", "saddle-saddle pairs", "saddle-max pairs"]
    for pt in pairsType:
        distmat = simple.TTKPersistenceDiagramDistanceMatrix(Input=thr)
        distmat.Criticalpairsused = pt
        ptf = pt.split()[0].replace("-", "_")
        simple.SaveData(f"dist_{stem}_{ptf}.csv", Input=distmat)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Compute distance matrices between a series of persistence diagrams"
        )
    )
    parser.add_argument("diag0", help="Path to first persistence diagram")
    args = parser.parse_args()
    main(args.diag0)

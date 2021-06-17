import argparse
import enum
import pathlib

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

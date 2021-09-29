#!/usr/bin/env python3

import argparse
import difflib
import math

import topologytoolkit as ttk
import vtk
from vtk.numpy_interface import dataset_adapter as dsa


def read_file(fname):
    ext = fname.split(".")[-1]
    if ext == "vtu":
        reader = vtk.vtkXMLUnstructuredGridReader()
    elif ext == "dipha":
        reader = ttk.ttkDiphaReader()
    elif ext == "gudhi":
        reader = ttk.ttkGudhiPersistenceDiagramReader()
    else:
        return None
    reader.SetFileName(fname)

    # filter out diagonal
    thr = vtk.vtkThreshold()
    thr.SetInputConnection(reader.GetOutputPort())
    thr.SetInputArrayToProcess(
        0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_CELLS, "PairType"
    )
    thr.ThresholdBetween(0, 3)
    thr.Update()

    return thr.GetOutput()


def read_diag(diag, filter_inf=False):
    diag = read_file(diag)

    if filter_inf:
        # filter infinite pairs?
        thr = vtk.vtkThreshold()
        thr.SetInputDataObject(diag)
        thr.SetInputArrayToProcess(
            0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_CELLS, "IsFinite"
        )
        thr.ThresholdBetween(1, 1)
        thr.Update()
        diag = thr.GetOutput()

    # filter out pairs with small to no persistence?
    thr2 = vtk.vtkThreshold()
    thr2.SetInputDataObject(diag)
    thr2.SetInputArrayToProcess(
        0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_CELLS, "Persistence"
    )
    thr2.ThresholdBetween(0, 1)
    thr2.SetInvert(True)

    pairs = [[] for i in range(3)]
    for i in range(3):
        thr = vtk.vtkThreshold()
        thr.SetInputConnection(thr2.GetOutputPort())
        thr.SetInputArrayToProcess(
            0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_CELLS, "PairType"
        )
        thr.ThresholdBetween(i, i)
        thr.Update()

        diag = dsa.WrapDataObject(thr.GetOutput())
        pts = diag.Points
        for j, pt in enumerate(pts):
            if j % 2 == 0:
                continue
            pairs[i].append((pt[0], pt[1]))

    for pr in pairs:
        pr.sort()

    return pairs


def print_diff(pairs0, pairs1):
    p0 = [str(a) + " " + str(b) for (a, b) in pairs0]
    p1 = [str(a) + " " + str(b) for (a, b) in pairs1]
    diff = difflib.unified_diff(p0, p1)
    GREEN = "\033[92m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    for d in diff:
        if d.startswith("+"):
            print(f"{GREEN}{d}{ENDC}")
        elif d.startswith("-"):
            print(f"{RED}{d}{ENDC}")
        else:
            print(d)


def wasserstein_pairs(pairs0, pairs1, timeout=3600):
    # store rem0 and rem1 in temporary files
    with open("/tmp/diag0.gudhi", "w") as dst:
        for b, d in pairs0:
            dst.write(f"0 {b} {d}\n")
    with open("/tmp/diag1.gudhi", "w") as dst:
        for b, d in pairs1:
            dst.write(f"0 {b} {d}\n")

    # compute the distance with bottleneck
    import diagram_distance as diagdist

    dists = diagdist.get_diag_dist(
        "/tmp/diag0.gudhi",
        "/tmp/diag1.gudhi",
        1.0,
        diagdist.DistMethod.AUCTION,
        timeout,
    )

    return dists["sad-max"]


def compare_pairs(pairs0, pairs1, ptype, show_diff):
    sm = difflib.SequenceMatcher(isjunk=None, a=pairs0, b=pairs1)
    if math.isclose(sm.ratio(), 1.0):
        print(f"> Identical {ptype} pairs")
        return 0.0

    if show_diff:
        print_diff(pairs0, pairs1)

    # discard common pairs between diagrams
    rem0, rem1 = [], []
    for opc in sm.get_opcodes():
        if opc[0] in ["replace", "delete"]:
            sl = slice(opc[1], opc[2])
            rem0.extend(pairs0[sl])
        if opc[0] in ["replace", "insert"]:
            sl = slice(opc[3], opc[4])
            rem1.extend(pairs1[sl])

    def dist_to_empty(pairs):
        # compute the distance from pairs0 to the empty diagram
        # (sum of square of pairs persistence divided by 2)
        sq_dist = sum((d - b) ** 2 for (b, d) in pairs) / 2.0
        return math.sqrt(sq_dist)

    print(f"  Comparing {len(rem0)} and {len(rem1)} different {ptype} pair...")

    if len(rem0) == 0:
        # compute distance between rem1 and empty diagram
        wass_dist = dist_to_empty(rem1)
    elif len(rem1) == 0:
        # compute distance between rem0 and empty diagram
        wass_dist = dist_to_empty(rem0)
    else:
        try:
            # compute wasserstein distance between rem0 and rem1
            wass_dist = wasserstein_pairs(rem0, rem1)
        except (ImportError, TypeError):
            print("Could not compute the Wassertein distance")
            return -1.0

    # compute the distance from pairs0 to the empty diagram
    ref_dist = dist_to_empty(pairs0)

    print(
        f"> Differences in {ptype} pairs "
        f"(Wasserstein approx: {wass_dist:.8g}, {wass_dist/ref_dist:.3%} from empty diagram)"
    )
    return wass_dist / ref_dist


def main(diag0, diag1, show_diff=True, filter_inf=False):
    print(f"\nComparing {diag0} and {diag1}...")
    pairs0 = read_diag(diag0, filter_inf)
    pairs1 = read_diag(diag1, filter_inf)
    if len(pairs0[1]) == 0:
        diag_type = ["min-max"]
    elif len(pairs0[2]) == 0:
        diag_type = ["min-saddle", "saddle-max"]
    else:
        diag_type = ["min-saddle", "saddle-saddle", "saddle-max"]
    res = {}
    for p0, p1, t in zip(pairs0, pairs1, diag_type):
        res[t] = compare_pairs(p0, p1, t, show_diff)
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare two diagrams with Python difflib"
    )
    parser.add_argument("diag0", help="First diagram")
    parser.add_argument("diag1", help="Second diagram")
    parser.add_argument("-s", "--show_diff", help="Show diff", action="store_true")
    parser.add_argument(
        "-f", "--filter_inf", help="Only consider finite pairs", action="store_true"
    )

    args = parser.parse_args()
    main(args.diag0, args.diag1, args.show_diff, args.filter_inf)

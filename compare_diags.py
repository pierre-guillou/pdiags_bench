#!/usr/bin/env python3

import argparse
import difflib
import itertools
import math

import topologytoolkit as ttk
import vtk


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
    reader.Update()
    return reader.GetOutput()


def read_diag(diag):
    diag = read_file(diag)
    ptype = diag.GetCellData().GetArray("PairType")
    pts = diag.GetPoints()
    if pts is None:
        return []
    assert 2 * ptype.GetNumberOfTuples() - 2 == pts.GetNumberOfPoints()
    pairs = [list() for i in range(3)]
    for i in range(ptype.GetNumberOfTuples()):
        j = int(ptype.GetTuple1(i))
        if j == -1:
            continue
        pairs[j].append(pts.GetPoint(2 * i + 1)[0:2])
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


def compare_pairs(pairs0, pairs1, ptype, show_diff):
    sm = difflib.SequenceMatcher(isjunk=None, a=pairs0, b=pairs1)
    diffrat = sm.ratio()
    if math.isclose(diffrat, 1.0):
        print(f"> Identical {ptype} pairs")
        return 0.0

    if show_diff:
        print_diff(pairs0, pairs1)

    # discard common pairs between diagrams
    rem0 = list()
    rem1 = list()
    for opc in sm.get_opcodes():
        if opc[0] in ["replace", "delete"]:
            sl = slice(opc[1], opc[2])
            rem0.extend(pairs0[sl])
        if opc[0] in ["replace", "insert"]:
            sl = slice(opc[3], opc[4])
            rem1.extend(pairs1[sl])

    # compute an overapproximation of the Wasserstein distance
    res = 0.0
    for (ba, da), (bb, db) in itertools.zip_longest(rem0, rem1, fillvalue=(0.0, 0.0)):
        res += (bb - ba) ** 2 + (db - da) ** 2

    # compute the distance from pairs0 to the empty diagram
    # (sum of pairs persistence divided by sqrt(2))
    ref_dist = sum(d - b for (b, d) in pairs0) / math.sqrt(2.0)

    wass_dist = math.sqrt(res)

    print(
        f"> Differences in {ptype} pairs "
        f"(Wasserstein approx: {wass_dist:.8g}, {wass_dist/ref_dist:.3%} from empty diagram)"
    )
    return wass_dist


def main(diag0, diag1, show_diff=True):
    print(f"Comparing {diag0} and {diag1}...")
    pairs0 = read_diag(diag0)
    pairs1 = read_diag(diag1)
    if len(pairs0[1]) == 0:
        diag_type = ["min-max"]
    elif len(pairs0[2]) == 0:
        diag_type = ["min-saddle", "saddle-max"]
    else:
        diag_type = ["min-saddle", "saddle-saddle", "saddle-max"]
    res = dict()
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

    args = parser.parse_args()
    main(args.diag0, args.diag1, args.show_diff)

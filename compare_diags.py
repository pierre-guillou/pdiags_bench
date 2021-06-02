#!/usr/bin/env python3

import difflib
import glob
import math
import sys

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
    assert 2 * ptype.GetNumberOfTuples() - 2 == pts.GetNumberOfPoints()
    pairs = [list() for i in range(3)]
    for i in range(ptype.GetNumberOfTuples()):
        j = int(ptype.GetTuple1(i))
        if j == -1:
            continue
        pairs[j].append(pts.GetPoint(2 * i + 1)[0:2])
    for pr in pairs:
        pr.sort(key=lambda x: x[1])
    return pairs


def compare_pairs(pairs0, pairs1, ptype, show_diff):
    sm = difflib.SequenceMatcher(isjunk=None, a=pairs0, b=pairs1)
    diffrat = sm.ratio()
    if math.isclose(diffrat, 1.0):
        print(f"> Identical {ptype} pairs")
    else:
        print(f"> Differences in {ptype} pairs (similarity ratio: {diffrat})")
        if show_diff:
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


def main(diag0, diag1, show_diff=True):
    print(f"Comparing {diag0} and {diag1}...")
    pairs0 = read_diag(diag0)
    pairs1 = read_diag(diag1)
    diag_type = ["min-saddle", "saddle-saddle", "saddle-max"]
    for p0, p1, t in zip(pairs0, pairs1, diag_type):
        compare_pairs(p0, p1, t, show_diff)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2], True)
    else:
        expl_diags = sorted(glob.glob("diagrams/*_order_sfnorm_expl*"))
        for k in range(len(expl_diags) // 2):
            main(expl_diags[2 * k], expl_diags[2 * k + 1])

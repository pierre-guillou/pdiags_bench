#!/usr/bin/env python3

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
    else:
        return None
    reader.SetFileName(fname)
    reader.Update()
    return reader.GetOutput()


def read_diag(diag):
    diag = read_file(diag)
    ptype = diag.GetCellData().GetArray("PairType")
    ppers = diag.GetCellData().GetArray("Persistence")
    assert ptype.GetNumberOfTuples() == ppers.GetNumberOfTuples()
    pairs = [list() for i in range(3)]
    for i in range(ptype.GetNumberOfTuples()):
        j = int(ptype.GetTuple1(i))
        if j == -1:
            continue
        pairs[j].append(ppers.GetTuple1(i))
    for pr in pairs:
        pr.sort(reverse=True)
    return pairs


def compare_pairs(pairs0, pairs1, type):
    diff = 0
    for i, (p0, p1) in enumerate(zip(pairs0, pairs1)):
        if not math.isclose(p0, p1, rel_tol=1e-7):
            if diff == 0:
                p = f"{i}, {p0}, {p1}"
            diff += 1

    if diff == 0:
        print(f"> Identical {type} pairs")
    else:
        print(f"> {diff}/{len(pairs0)} different {type} pairs ({p})")


def main(diag0, diag1):
    print(f"Comparing {diag0} and {diag1}...")
    pairs0 = read_diag(diag0)
    pairs1 = read_diag(diag1)
    diag_type = ["min-saddle", "saddle-saddle", "saddle-max"]
    for p0, p1, t in zip(pairs0, pairs1, diag_type):
        compare_pairs(p0, p1, t)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        expl_diags = sorted(glob.glob("diagrams/*_order_sfnorm_expl*"))
        for i in range(len(expl_diags) // 2):
            main(expl_diags[2 * i], expl_diags[2 * i + 1])

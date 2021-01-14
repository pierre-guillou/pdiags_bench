#!/usr/bin/env python3

import glob
import math
import operator
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


class PersistencePair:
    def __init__(self, type, persistence):
        self.type = int(type)
        self.persistence = persistence

    def __repr__(self):
        return f"{{{self.type}, {self.persistence}}}"


def read_diag(diag):
    diag = read_file(diag)
    ptype = diag.GetCellData().GetArray("PairType")
    ppers = diag.GetCellData().GetArray("Persistence")
    assert ptype.GetNumberOfTuples() == ppers.GetNumberOfTuples()
    pairs = list()
    for i in range(ptype.GetNumberOfTuples()):
        pairs.append(PersistencePair(ptype.GetTuple1(i), ppers.GetTuple1(i)))
    pairs.sort(key=operator.attrgetter("type", "persistence"), reverse=True)
    return pairs


def main(diag0, diag1):
    print(f"Comparing {diag0} and {diag1}...")
    pairs0 = read_diag(diag0)
    pairs1 = read_diag(diag1)
    for (i, (p0, p1)) in enumerate(zip(pairs0, pairs1)):
        if p0.type != p1.type or not math.isclose(
            p0.persistence, p1.persistence, rel_tol=1e-7
        ):
            print(f"> {i} ({i / len(pairs0) * 100:.1f}%), {p0}, {p1}")
            return
    print("> Identical diagrams")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        expl_diags = sorted(glob.glob("diagrams/*_order_sfnorm_expl*"))
        for i in range(len(expl_diags) // 2):
            main(expl_diags[2 * i], expl_diags[2 * i + 1])

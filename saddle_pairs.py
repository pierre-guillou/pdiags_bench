import os
import subprocess

import numpy as np
from paraview import servermanager, simple
from paraview.vtk.numpy_interface import dataset_adapter as dsa

import compare_diags

DIR = "rndsmoo"


def gen_randoms(seed):
    fug = simple.FastUniformGrid()
    fug.WholeExtent = [0, 64, 0, 64, 0, 64]

    tetrah = simple.Tetrahedralize(Input=fug)

    ra = simple.RandomAttributes(Input=tetrah)
    ra.DataType = "Int"
    ra.GeneratePointScalars = 1
    ra.GenerateCellVectors = 0

    vtk_ra = servermanager.Fetch(ra)
    data = dsa.WrapDataObject(vtk_ra)
    array = data.PointData["RandomPointScalars"]
    gen = np.random.default_rng(seed)
    gen.shuffle(array)

    smoo = simple.TTKScalarFieldSmoother(Input=ra)
    smoo.ScalarField = ["POINTS", "RandomPointScalars"]
    smoo.IterationNumber = 55
    simp = simple.TTKTopologicalSimplificationByPersistence(Input=smoo)
    simp.InputArray = ["POINTS", "RandomPointScalars"]
    simp.PersistenceThreshold = 200

    pa = simple.PassArrays(Input=simp)
    pa.PointDataArrays = ["RandomPointScalars_Order"]

    rgi = simple.RemoveGhostInformation(Input=pa)

    simple.SaveData(f"{DIR}/test{seed}.dipha", Input=rgi)
    simple.SaveData(f"{DIR}/test{seed}.vtu", Input=rgi)


def compute_dipha_diag(seed):
    print(f"Calling Dipha on {DIR}/test{seed}.dipha...")
    subprocess.check_call(
        ["build_dipha/dipha", f"{DIR}/test{seed}.dipha", f"{DIR}/out{seed}.dipha"]
    )


def compute_ttk_diag(seed):
    reader = simple.XMLUnstructuredGridReader(FileName=f"{DIR}/test{seed}.vtu")

    pdiag = simple.TTKPersistenceDiagram(Input=reader)
    pdiag.ScalarField = ["POINTS", "RandomPointScalars_Order"]
    pdiag.Backend = "DMT Pairs"
    pdiag.IgnoreBoundary = False
    pdiag.DebugLevel = 4

    simple.SaveData(f"{DIR}/out{seed}.vtu", Input=pdiag)


def compare(seed):
    res = compare_diags.main(
        f"{DIR}/out{seed}.dipha", f"{DIR}/out{seed}.vtu", True, False
    )
    if any(v != 0.0 for v in res.values()):
        print(f"Differences for seed {seed}")
        return False
    return True


def main():
    try:
        os.mkdir(DIR)
    except FileExistsError:
        pass

    prepare = True
    gen_ttk = False
    comp = False
    diff = []

    for seed in range(500):
        print(f"Seed {seed}")
        if prepare:
            gen_randoms(seed)
            compute_dipha_diag(seed)
        if gen_ttk:
            compute_ttk_diag(seed)
        if comp:
            ident = compare(seed)
            if not ident:
                diff.append(seed)

    if len(diff) > 0:
        print(f"Differences for #{len(diff)} seeds: {diff}")


if __name__ == "__main__":
    main()

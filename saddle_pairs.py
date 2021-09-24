import subprocess
import sys

import numpy as np
from paraview import servermanager, simple
from paraview.vtk.numpy_interface import dataset_adapter as dsa

import compare_diags


def main(seed):

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

    simple.SaveData("test.dipha", Input=rgi)
    simple.SaveData("test.vtu", Input=rgi)

    pdiag = simple.TTKPersistenceDiagram(Input=rgi)
    pdiag.ScalarField = ["POINTS", "RandomPointScalars_Order"]
    pdiag.Backend = "DMT Pairs"
    pdiag.IgnoreBoundary = False
    pdiag.DebugLevel = 4

    simple.SaveData("out.vtu", Input=pdiag)

    print("Calling Dipha...")
    subprocess.check_call(["build_dipha/dipha", "test.dipha", "out.dipha"])

    res = compare_diags.main("out.dipha", "out.vtu", True, False)
    if any(v != 0.0 for v in res.values()):
        sys.exit(1)


if __name__ == "__main__":
    for s in range(500):
        print(f"Seed {s}")
        main(s)

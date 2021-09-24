import subprocess

from paraview import simple

import compare_diags

fug = simple.FastUniformGrid()
fug.WholeExtent = [0, 64, 0, 64, 0, 64]

tetrah = simple.Tetrahedralize(Input=fug)

ra = simple.RandomAttributes(Input=tetrah)
ra.DataType = "Int"
ra.GeneratePointScalars = 1
ra.GenerateCellVectors = 0

smoo = simple.TTKScalarFieldSmoother(Input=ra)
smoo.ScalarField = ["POINTS", "RandomPointScalars"]
smoo.IterationNumber = 44

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

compare_diags.main("out.dipha", "out.vtu", True, False)

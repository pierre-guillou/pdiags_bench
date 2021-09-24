import subprocess

from paraview import simple

import compare_diags

vti = simple.XMLImageDataReader(FileName=["../ttk-data/BuiltInExample2.vti"])
vti.PointArrayStatus = ["log(s)"]
vti.TimeArray = "None"

rsi = simple.ResampleToImage(Input=vti)
rsi.SamplingDimensions = [64, 64, 64]
rsi.SamplingBounds = [0.0, 114.0, 0.0, 115.0, 0.0, 133.0]

tetrah = simple.Tetrahedralize(Input=rsi)

thr = simple.Threshold(Input=tetrah)
thr.Scalars = ["POINTS", "log(s)"]
thr.ThresholdRange = [-0.5, 1.7097323412037762]

ra = simple.RandomAttributes(Input=thr)
ra.DataType = "Int"
ra.GeneratePointScalars = 1
ra.GenerateCellVectors = 0

pa = simple.PassArrays(Input=ra)
pa.PointDataArrays = ["RandomPointScalars"]

rgi = simple.RemoveGhostInformation(Input=pa)

smoo = simple.TTKScalarFieldSmoother(Input=rgi)
smoo.ScalarField = ["POINTS", "RandomPointScalars"]
smoo.IterationNumber = 20

simple.SaveData("test.dipha", Input=smoo)
simple.SaveData("test.vtu", Input=smoo)

pdiag = simple.TTKPersistenceDiagram(Input=smoo)
pdiag.ScalarField = ["POINTS", "RandomPointScalars"]
pdiag.InputOffsetField = ["POINTS", "RandomPointScalars"]
pdiag.Backend = "DMT Pairs"
pdiag.IgnoreBoundary = 0
pdiag.DebugLevel = 4

simple.SaveData("out.vtu", Input=pdiag)

print("Calling Dipha...")
subprocess.check_call(["build_dipha/dipha", "test.dipha", "out.dipha"])

compare_diags.main("out.dipha", "out.vtu", True, False)

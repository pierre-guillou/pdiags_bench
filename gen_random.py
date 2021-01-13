import sys

from paraview import simple

fug = simple.FastUniformGrid()
ext = int(sys.argv[1]) if len(sys.argv) > 0 else 8
fug.WholeExtent = [0, ext - 1, 0, ext - 1, 0, ext - 1]

if len(sys.argv) > 2 and sys.argv[2] == "elev":
    elev = simple.Elevation(Input=fug)
    elev.LowPoint = [0, 0, 0]
    elev.HighPoint = [ext - 1, ext - 1, ext - 1]

    pa = simple.PassArrays(Input=elev)
    pa.PointDataArrays = ["Elevation"]

    simple.SaveData("elevation.vti", Input=pa)

else:
    rattr = simple.RandomAttributes(Input=fug)
    rattr.DataType = "Float"
    rattr.ComponentRange = [0.0, 1.0]
    rattr.GeneratePointScalars = 1
    rattr.GenerateCellVectors = 0

    pa = simple.PassArrays(Input=rattr)
    pa.PointDataArrays = ["RandomPointScalars"]

    simple.SaveData("random.vti", Input=pa)

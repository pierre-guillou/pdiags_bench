from paraview import simple

fug = simple.FastUniformGrid()
ext = 40
fug.WholeExtent = [0, ext, 0, ext, 0, ext]

rattr = simple.RandomAttributes(Input=fug)
rattr.DataType = "Float"
rattr.ComponentRange = [0.0, 1.0]
rattr.GeneratePointScalars = 1
rattr.GenerateCellVectors = 0

pa = simple.PassArrays(Input=rattr)
pa.PointDataArrays = ["RandomPointScalars"]

simple.SaveData("random.vti", Input=pa)

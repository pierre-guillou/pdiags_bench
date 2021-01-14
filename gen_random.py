import sys

from paraview import simple


def main(ext, mode):
    fug = simple.FastUniformGrid()
    fug.WholeExtent = [0, ext - 1, 0, ext - 1, 0, ext - 1]

    if mode == "elev":
        elev = simple.Elevation(Input=fug)
        elev.LowPoint = [0, 0, 0]
        elev.HighPoint = [ext - 1, ext - 1, ext - 1]

        pa = simple.PassArrays(Input=elev)
        pa.PointDataArrays = ["Elevation"]

        simple.SaveData("elevation.vti", Input=pa)

    elif mode == "rand":
        rattr = simple.RandomAttributes(Input=fug)
        rattr.DataType = "Float"
        rattr.ComponentRange = [0.0, 1.0]
        rattr.GeneratePointScalars = 1
        rattr.GenerateCellVectors = 0

        pa = simple.PassArrays(Input=rattr)
        pa.PointDataArrays = ["RandomPointScalars"]

        simple.SaveData("random.vti", Input=pa)


if __name__ == "__main__":
    try:
        ext = int(sys.argv[1])
    except IndexError:
        ext = 8
    try:
        mode = sys.argv[2]
    except IndexError:
        mode = "rand"

    main(ext, mode)

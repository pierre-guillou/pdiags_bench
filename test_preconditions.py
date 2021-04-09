import argparse
import os

from paraview import simple


def main(vtu_path, read=False):
    vtu = simple.XMLUnstructuredGridReader(FileName=vtu_path)
    elev = simple.Elevation(Input=vtu)
    tri = elev
    if read:
        tri = simple.TTKTriangulationReader(Input=elev)
        tri.TriangulationFilePath = "test.tpt"
    msc = simple.TTKMorseSmaleComplex(Input=tri)
    msc.ScalarField = ["POINTS", "Elevation"]
    msc.OffsetField = ["POINTS", "Elevation"]
    if not read:
        simple.SaveData("test.tpt", proxy=simple.OutputPort(msc, 3))
    else:
        simple.SaveData("out.vtp", proxy=simple.OutputPort(msc, 1))
        os.remove("out.vtp")
        os.remove("test.tpt")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test read/write Explicit Triangulation performance"
    )
    parser.add_argument("VTU_File", type=str, help="Path to the .vtu input file")
    parser.add_argument(
        "-r", "--read", action="store_true", help="Read triangulation from disk"
    )
    args = parser.parse_args()
    main(args.VTU_File, args.read)

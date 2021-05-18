import argparse

from paraview import simple


def main(edge_size, field, dest_dir):
    fug = simple.FastUniformGrid()
    fug.WholeExtent = [0, edge_size - 1, 0, edge_size - 1, 0, edge_size - 1]

    sfname = {"elevation": "Elevation", "random": "RandomPointScalars"}

    if field == "elevation":
        sf = simple.Elevation(Input=fug)
        sf.LowPoint = [0, 0, 0]
        sf.HighPoint = [edge_size - 1, edge_size - 1, edge_size - 1]

    elif field == "random":
        sf = simple.RandomAttributes(Input=fug)
        sf.DataType = "Float"
        sf.ComponentRange = [0.0, 1.0]
        sf.GeneratePointScalars = 1
        sf.GenerateCellVectors = 0

    # rename scalar field to "ImageFile" (and convert it to float)
    calc = simple.Calculator(Input=sf)
    calc.Function = sfname[field]
    calc.ResultArrayType = "Float"
    calc.ResultArrayName = "ImageFile"

    # only keep "ImageFile" field
    pa = simple.PassArrays(Input=calc)
    pa.PointDataArrays = ["ImageFile"]

    simple.SaveData(f"{dest_dir}/{field}.vti", Input=pa)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a cubical grid with the given edge size "
        "with a random or an elevation scalar field"
    )

    parser.add_argument(
        "edge_size", help="Number of vertices per grid edge", type=int, default=8
    )
    parser.add_argument(
        "-f",
        "--field",
        choices=["elevation", "random"],
        help="Generated scalar field",
        default="random",
    )
    parser.add_argument("-d", "--dest_dir", help="Destination directory", default=".")

    args = parser.parse_args()

    main(args.edge_size, args.field, args.dest_dir)

import sys

from paraview import simple


def write_output(outp, fname, out_dir, explicit):
    if out_dir:
        fname = out_dir + "/" + fname
    if explicit:
        # vtkUnstructuredGrid (TTK)
        simple.SaveData(fname + ".vtu", proxy=outp)
    else:
        # Perseus Cubical Grid (Gudhi)
        simple.SaveData(fname + ".pers", proxy=outp)
    # Dipha Explicit Complex or Image Data (Dipha, CubicalRipser)
    simple.SaveData(fname + ".dipha", proxy=outp)


def main(raw_file, out_dir=""):
    extent, dtype = raw_file.split(".")[0].split("_")[-2:]
    extent = [int(dim) for dim in extent.split("x")]

    dtype_pv = {
        "uint8": "unsigned char",
        "int16": "short",
        "uint16": "unsigned short",
        "float32": "float",
        "float64": "double",
    }

    raw = simple.ImageReader(FileNames=[raw_file])
    raw.DataScalarType = dtype_pv[dtype]
    raw.DataExtent = [0, extent[0] - 1, 0, extent[1] - 1, 0, extent[2] - 1]
    raw_stem = raw_file.split(".")[0].split("/")[-1]

    # convert input scalar field to float
    pdc = simple.TTKPointDataConverter(Input=raw)
    pdc.PointDataScalarField = ["POINTS", "ImageFile"]
    pdc.OutputType = "Float"
    # resample to 192^3
    rsi = simple.ResampleToImage(Input=pdc)
    rsi.SamplingDimensions = [192, 192, 192]
    # compute order field
    arrprec = simple.TTKArrayPreconditioning(Input=rsi)
    arrprec.PointDataArrays = ["ImageFile"]
    # trash input scalar field, save order field
    pa = simple.PassArrays(Input=arrprec)
    pa.PointDataArrays = ["ImageFile_Order"]
    # save implicit mesh
    write_output(pa, raw_stem + "_order_impl", out_dir, False)

    # tetrahedralize grid
    tetrah = simple.Tetrahedralize(Input=pa)
    # remove vtkGhostType arrays (only applies on vtu & vtp)
    rgi = simple.RemoveGhostInformation(Input=tetrah)
    # save explicit mesh
    write_output(rgi, raw_stem + "_order_expl", out_dir, True)

    print("Converted " + raw_file + " to VTU and Dipha")


if __name__ == "__main__":
    if len(sys.argv) >= 1:
        main(*sys.argv[1:3])

import sys

from paraview import simple


def write_output(outp, fname, out_dir, explicit):
    if out_dir:
        fname = out_dir + "/" + fname
    if explicit:
        # vtkUnstructuredGrid (TTK)
        simple.SaveData(fname + ".vtu", proxy=outp)
    else:
        # vtkImageData (TTK)
        simple.SaveData(fname + ".vti", proxy=outp)
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
    # normalize scalar field
    sfnorm = simple.TTKScalarFieldNormalizer(Input=pdc)
    sfnorm.ScalarField = ["POINTS", "ImageFile"]
    # compute order field
    arrprec = simple.TTKArrayPreconditioning(Input=sfnorm)
    arrprec.PointDataArrays = ["ImageFile"]
    # convert order field to float
    pdc2 = simple.TTKPointDataConverter(Input=arrprec)
    pdc2.PointDataScalarField = ["POINTS", "ImageFile_Order"]
    pdc2.OutputType = "Float"
    # normalize order field
    sfnorm2 = simple.TTKScalarFieldNormalizer(Input=pdc2)
    sfnorm2.ScalarField = ["POINTS", "ImageFile_Order"]
    # trash input scalar field, save order field
    pa = simple.PassArrays(Input=sfnorm2)
    pa.PointDataArrays = ["ImageFile_Order"]
    # save implicit grid
    write_output(pa, raw_stem + "_order_sfnorm_impl", out_dir, False)

    # tetrahedralize grid
    tetrah = simple.Tetrahedralize(Input=pa)
    # save explicit mesh
    write_output(tetrah, raw_stem + "_order_sfnorm_expl", out_dir, True)

    print("Converted " + raw_file + " to VTU and Dipha")


if __name__ == "__main__":
    if len(sys.argv) >= 1:
        main(*sys.argv[1:3])

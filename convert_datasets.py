import argparse

from paraview import simple

import vti2nc3

RESAMPL = 192


def write_output(outp, fname, out_dir, explicit):
    if out_dir:
        fname = out_dir + "/" + fname

    # Dipha Explicit Complex (Dipha) or Image Data (Dipha, CubicalRipser)
    simple.SaveData(fname + ".dipha", proxy=outp)

    if explicit:
        # vtkUnstructuredGrid (TTK)
        simple.SaveData(fname + ".vtu", proxy=outp)
        # TTK Simplicial Complex (Gudhi, Dionysus, Ripser)
        simple.SaveData(fname + ".tsc", proxy=outp)
        # Perseus Uniform Triangulation (Perseus)
        simple.SaveData(fname + ".pers", proxy=outp)
        # Eirene.jl Sparse Column Format CSV
        simple.SaveData(fname + ".eirene", proxy=outp)
    else:
        # vtkImageData (TTK)
        simple.SaveData(fname + ".vti", proxy=outp)
        # Perseus Cubical Grid (Perseus, Gudhi)
        simple.SaveData(fname + ".pers", proxy=outp)
        # NetCDF3 (Diamorse)
        vti2nc3.main(fname + ".vti")


def read_file(input_file):
    extension = input_file.split(".")[-1]
    if extension == "vti":
        return simple.XMLImageDataReader(FileName=input_file)

    if extension == "raw":
        extent, dtype = input_file.split(".")[0].split("_")[-2:]
        extent = [int(dim) for dim in extent.split("x")]

        dtype_pv = {
            "uint8": "unsigned char",
            "int16": "short",
            "uint16": "unsigned short",
            "float32": "float",
            "float64": "double",
        }

        raw = simple.ImageReader(FileNames=[input_file])
        raw.DataScalarType = dtype_pv[dtype]
        raw.DataExtent = [0, extent[0] - 1, 0, extent[1] - 1, 0, extent[2] - 1]
        return raw

    return None


def main(raw_file, out_dir="", resampl_size=RESAMPL):
    if raw_file == "":
        return

    print(f"Converting {raw_file} to input formats (resampled to {resampl_size}^3)")

    raw_stem = raw_file.split(".")[0].split("/")[-1]
    reader = read_file(raw_file)
    extent_s = "x".join([str(resampl_size)] * 3)
    try:
        raw_stem_parts = raw_stem.split("_")
        raw_stem_parts[-2] = extent_s
        raw_stem = "_".join(raw_stem_parts)
    except IndexError:
        # not an Open-Scivis-Datasets raw file (elevation or random)
        raw_stem = f"{raw_stem}_{extent_s}"

    # convert input scalar field to float
    calc = simple.Calculator(Input=reader)
    calc.Function = "ImageFile"
    calc.ResultArrayType = "Float"
    calc.ResultArrayName = "ImageFile"
    # resample to 192^3
    rsi = simple.ResampleToImage(Input=calc)
    rsi.SamplingDimensions = [resampl_size] * 3
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

    print("Converted " + raw_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate input files from Open-Scivis Raw format"
    )

    parser.add_argument("raw_file", type=str, help="Path to input Raw file")
    parser.add_argument(
        "-d", "--dest_dir", type=str, help="Destination directory", default="datasets"
    )
    parser.add_argument(
        "-s",
        "--resampling_size",
        type=int,
        help="Resampling to a cube of given vertices edge",
        default=RESAMPL,
    )

    args = parser.parse_args()

    main(args.raw_file, args.dest_dir, args.resampling_size)

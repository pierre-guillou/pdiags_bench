import argparse
import time

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


def slice_vti(input_vti, resampl_size=RESAMPL, for_implicit=True):
    # force generation of input_vti (otherwise, slice is empty)
    simple.Show(input_vti)
    sl = simple.Slice(Input=input_vti)
    # slice along depth/z axis
    sl.SliceType.Normal = [0.0, 0.0, 1.0]
    if for_implicit:
        # slice are Polygonal Meshes
        rsi = simple.ResampleToImage(Input=sl)
        rsi.SamplingDimensions = [resampl_size, resampl_size, 1]
        # trash input scalar field, save order field
        pa = simple.PassArrays(Input=rsi)
        pa.PointDataArrays = ["ImageFile_Order"]
        return pa
    return sl


def main(raw_file, out_dir="", resampl_size=RESAMPL, slice2d=False):
    if raw_file == "":
        return

    print(f"Converting {raw_file} to input formats (resampled to {resampl_size}^3)")
    beg = time.time()

    raw_stem = raw_file.split(".")[0].split("/")[-1]
    reader = read_file(raw_file)
    extent_s = "x".join([str(resampl_size)] * 3)
    try:
        raw_stem_parts = raw_stem.split("_")
        # update extent
        raw_stem_parts[-2] = extent_s
        # remove data type in file name
        raw_stem_parts.pop()
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
    out_vti = pa
    if slice2d:
        out_vti = slice_vti(pa, resampl_size, True)
    write_output(out_vti, raw_stem + "_order_impl", out_dir, False)

    if slice2d:
        pa = slice_vti(pa, resampl_size, False)
    # tetrahedralize grid
    tetrah = simple.Tetrahedralize(Input=pa)
    # remove vtkGhostType arrays (only applies on vtu & vtp)
    rgi = simple.RemoveGhostInformation(Input=tetrah)
    # save explicit mesh
    write_output(rgi, raw_stem + "_order_expl", out_dir, True)
    end = time.time()

    print(f"Converted {raw_file} (took {round(end - beg, 3)}s)")


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
    parser.add_argument(
        "-2",
        "--slice",
        action="store_true",
        help="Generate a 2D slice",
    )

    args = parser.parse_args()

    main(args.raw_file, args.dest_dir, args.resampling_size, args.slice)

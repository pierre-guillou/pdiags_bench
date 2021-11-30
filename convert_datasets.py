import argparse
import enum
import logging
import time

from paraview import simple

import vti2nc3

RESAMPL_3D = 192
RESAMPL_2D = 768
RESAMPL_1D = 1024 ** 2
logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)


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
        raw.DataByteOrder = "LittleEndian"
        raw.DataExtent = [0, extent[0] - 1, 0, extent[1] - 1, 0, extent[2] - 1]
        return raw

    return None


class SliceType(enum.Enum):
    VOL = 0
    SURF = 1
    LINE = 2

    @classmethod
    def from_filename(cls, fname):
        if "x1x1_" in fname:
            return cls.LINE
        if "x1_" in fname:
            return cls.SURF
        return cls.VOL


def slice_data(input_dataset, slice_type, dims):
    if slice_type in (SliceType.SURF, SliceType.LINE):
        # force generation of input_vti (otherwise, slice is empty)
        simple.Show(input_dataset)
        # slice along depth/z axis
        sl0 = simple.Slice(Input=input_dataset)
        sl0.SliceType.Normal = [0.0, 0.0, 1.0]

        if slice_type == SliceType.LINE:
            # resample to a 2D strip before slicing again
            rsi = simple.ResampleToImage(Input=sl0)
            rsi.SamplingDimensions = [dims[0], 3, 1]
            simple.Show(rsi)  # same here...

            # slice along vertical/y axis
            sl1 = simple.Slice(Input=rsi)
            sl1.SliceType.Normal = [0.0, 1.0, 0.0]
            return sl1

        # resample to something like 768x768x1
        rsi = simple.ResampleToImage(Input=sl0)
        rsi.SamplingDimensions = dims
        return rsi

    # resample to something like 192^3
    rsi = simple.ResampleToImage(Input=input_dataset)
    rsi.SamplingDimensions = dims
    return rsi


def pipeline(raw_file, raw_stem, dims, slice_type, out_dir):
    reader = read_file(raw_file)
    # convert input scalar field to float
    calc = simple.Calculator(Input=reader)
    calc.Function = "ImageFile"
    calc.ResultArrayType = "Float"
    calc.ResultArrayName = "ImageFile"

    # get a slice
    cut = slice_data(calc, slice_type, dims)

    # trash input scalar field, save order field
    pa = simple.PassArrays(Input=cut)
    pa.PointDataArrays = ["ImageFile"]

    # tetrahedralize grid
    tetrah = simple.Tetrahedralize(Input=pa)
    # remove vtkGhostType arrays (only applies on vtu & vtp)
    rgi = simple.RemoveGhostInformation(Input=tetrah)
    # save explicit mesh
    write_output(rgi, raw_stem + "_order_expl", out_dir, True)


def main(raw_file, out_dir="", resampl_size=RESAMPL_3D, slice_type=SliceType.VOL):
    if raw_file == "":
        return

    if slice_type == SliceType.VOL:
        dims = [resampl_size] * 3
    elif slice_type == SliceType.SURF:
        dims = [resampl_size] * 2 + [1]
    elif slice_type == SliceType.LINE:
        dims = [resampl_size] + [1] * 2
    extent_s = "x".join([str(d) for d in dims])

    raw_stem = raw_file.split(".")[0].split("/")[-1]
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

    logging.info("Converting %s to input formats (resampled to %s)", raw_file, extent_s)
    beg = time.time()

    pipeline(raw_file, raw_stem, dims, slice_type, out_dir)

    end = time.time()
    logging.info("Converted %s (took %ss)", raw_file, round(end - beg, 3))


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
    )
    parser.add_argument(
        "-2",
        "--slice",
        action="store_true",
        help="Generate a 2D slice",
    )
    parser.add_argument(
        "-1",
        "--line",
        action="store_true",
        help="Generate a 1D line",
    )
    args = parser.parse_args()

    if args.line and args.slice:
        raise argparse.ArgumentError

    if args.slice:
        stype = SliceType.SURF
        if args.resampling_size is None:
            args.resampling_size = RESAMPL_2D
    elif args.line:
        stype = SliceType.LINE
        if args.resampling_size is None:
            args.resampling_size = RESAMPL_1D
    else:
        stype = SliceType.VOL
        if args.resampling_size is None:
            args.resampling_size = RESAMPL_3D

    main(args.raw_file, args.dest_dir, args.resampling_size, stype)

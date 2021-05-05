import argparse

import netCDF4 as nc
import vtk
from vtk.util.numpy_support import vtk_to_numpy


def main(input_vti, output_nc3=None):
    if output_nc3 is None:
        ext = input_vti.split(".")[-1]
        output_nc3 = input_vti.replace(ext, "nc")

    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(input_vti)
    reader.Update()

    image_data = reader.GetOutput()
    dims = list(image_data.GetDimensions())
    array = image_data.GetPointData().GetAbstractArray(0)
    if array.GetName() == "vtkGhostType":
        array = image_data.GetPointData().GetAbstractArray(1)
    array_name = array.GetName()
    array = vtk_to_numpy(array)

    with nc.Dataset(output_nc3, "w", format="NETCDF3_CLASSIC") as dst:
        dim_names = ["x", "y", "z"]
        for n, v in zip(dim_names, dims):
            dst.createDimension(n, v)
        data = dst.createVariable(array_name, "f8", dim_names)
        data[:, :, :] = array.reshape(dims)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Converts a VTK Image Data file to NetCDF3"
    )
    parser.add_argument("input_vti", help="Input VTI file")
    parser.add_argument("-o", "--output", help="Output NetCDF3 file")
    args = parser.parse_args()

    main(args.input_vti, args.output)

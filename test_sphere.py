import numpy as np
import vtk
from vtk.numpy_interface import dataset_adapter as dsa


def main():
    extent = (50, 50, 50)
    im = vtk.vtkImageData()
    im.SetDimensions(*extent)

    mask = vtk.vtkSignedCharArray()
    mask.SetNumberOfTuples(im.GetNumberOfPoints())
    mask.SetName("Mask")
    mask.Fill(0)
    im.GetPointData().AddArray(mask)

    dataset = dsa.WrapDataObject(im)
    array = dataset.PointData["Mask"].reshape(extent)

    orig = np.array(extent) / 2
    it = np.nditer(array, flags=["multi_index"])
    for _ in it:
        dist_orig = np.linalg.norm(np.array(it.multi_index) - orig)
        if .1 * extent[0] < dist_orig < .4 * extent[0]:
            array[it.multi_index] = 1

    thr = vtk.vtkThreshold()
    thr.SetInputData(im)
    thr.SetInputArrayToProcess(
        0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, "Mask"
    )
    thr.ThresholdBetween(1, 1)

    tetrah = vtk.vtkDataSetTriangleFilter()
    tetrah.SetInputConnection(0, thr.GetOutputPort())

    pid = vtk.vtkIdFilter()
    pid.SetInputConnection(0, tetrah.GetOutputPort())
    pid.SetPointIds(True)
    pid.SetCellIds(False)
    pid.SetPointIdsArrayName("ttkVertexScalarField")

    wr = vtk.vtkXMLUnstructuredGridWriter()
    wr.SetInputConnection(0, pid.GetOutputPort())
    wr.SetFileName("out.vtu")
    wr.Write()


if __name__ == "__main__":
    main()

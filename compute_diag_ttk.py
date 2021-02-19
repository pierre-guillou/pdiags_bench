import sys

from paraview import simple


def main(fname, nthreads=1, useDipha=False):
    # load dataset
    vtu = simple.XMLUnstructuredGridReader(FileName=[fname])
    # compute persistence diagram
    pdiag = simple.TTKPersistenceDiagram(Input=vtu)
    pdiag.ScalarField = ["POINTS", "ImageFile_Order"]
    pdiag.ComputepairswiththeDiscreteGradient = True
    pdiag.IgnoreBoundary = True
    pdiag.ComputepairswithDipha = useDipha
    pdiag.UseAllCores = False
    pdiag.ThreadNumber = int(nthreads)
    # save diagram
    simple.SaveData("output_port_0.vtu", Input=pdiag)
    # convert preconditionned input VTU as Dipha file
    simple.SaveData(fname.split(".")[0] + ".dipha", Input=vtu)


if __name__ == "__main__":
    if len(sys.argv) >= 1:
        main(*sys.argv[1:4])

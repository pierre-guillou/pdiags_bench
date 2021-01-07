import sys

from paraview import simple

# call it with `python ttk_diagram.py [bottleneck|auction] diagram0 diagram1`


def load_diagram(diag):
    if diag.endswith("vtu"):
        return simple.XMLUnstructuredGridReader(FileName=diag)
    elif diag.endswith("dipha") or diag.endswith("cr"):
        return simple.TTKDiphaPersistenceDiagramReader(FileName=diag)
    elif diag.endswith("gudhi"):
        return simple.TTKGudhiPersistenceDiagramReader(FileName=diag)


diag0 = load_diagram(sys.argv[2])
diag1 = load_diagram(sys.argv[3])
thr_bound = 0.01


if sys.argv[1] == "bottleneck":

    thr0 = simple.Threshold(Input=diag0)
    thr0.Scalars = ["CELLS", "Persistence"]
    thr0.ThresholdRange = [thr_bound, 1.0]

    thr1 = simple.Threshold(Input=diag1)
    thr1.Scalars = ["CELLS", "Persistence"]
    thr1.ThresholdRange = [thr_bound, 1.0]

    dist = simple.TTKBottleneckDistance(
        Persistencediagram1=thr0,
        Persistencediagram2=thr1,
    )

    save = simple.SaveData("dist.vtu", Input=dist)

elif sys.argv[1] == "auction":

    gd = simple.GroupDatasets(Input=[diag0, diag1])
    thr = simple.Threshold(Input=gd)
    thr.Scalars = ["CELLS", "Persistence"]
    thr.ThresholdRange = [thr_bound, 1.0]
    dist = simple.TTKPersistenceDiagramClustering(Input=thr)
    dist.Maximalcomputationtimes = 10.0
    save = simple.SaveData("dist.vtu", Input=dist)

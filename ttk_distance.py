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

if sys.argv[1] == "bottleneck":

    dist = simple.TTKBottleneckDistance(
        Persistencediagram1=diag0,
        Persistencediagram2=diag1,
    )

elif sys.argv[1] == "auction":

    gd = simple.GroupDatasets(Input=[diag0, diag1])
    dist = simple.TTKPersistenceDiagramClustering(Input=gd)
    dist.Maximalcomputationtimes = 10.0

save = simple.SaveData("dist.vtu", Input=dist)

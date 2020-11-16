import sys

from paraview import simple

# call it with `python ttk_diagram.py dataset.vti diagram.vtu`

data = simple.XMLImageDataReader(FileName=[sys.argv[1]])
pdiag = simple.TTKPersistenceDiagram(Input=data)
pdiag.ScalarField = ["POINTS", "ImageFile"]
pdiag.InputOffsetField = ["POINTS", "ImageFile"]
pdiag.ComputepairswiththeDiscreteGradient = True
pdiag.IgnoreBoundary = False
save = simple.SaveData(sys.argv[2], Input=pdiag)

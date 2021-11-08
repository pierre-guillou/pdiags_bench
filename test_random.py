import os
import shutil
import subprocess
import time

from paraview import simple

import compare_diags


def generate_random(extent, out, rs):
    # generate regular grid
    fug = simple.FastUniformGrid()
    fug.WholeExtent = [0, extent[0] - 1, 0, extent[1] - 1, 0, extent[2] - 1]

    # generate scalar field
    gid = simple.GenerateIds(Input=fug)
    gid.PointIdsArrayName = "ImageFile"
    gid.GenerateCellIds = False

    # convert from vtkIdType to int
    calc = simple.Calculator(Input=gid)
    calc.Function = "ImageFile"
    calc.ResultArrayType = "Int"
    calc.ResultArrayName = "ImageFile_Order"

    # trash input scalar field, save order field
    pa = simple.PassArrays(Input=calc)
    pa.PointDataArrays = ["ImageFile_Order"]

    # randomize scalar field
    ir = simple.TTKIdentifierRandomizer(Input=pa)
    ir.ScalarField = ["POINTS", "ImageFile_Order"]
    ir.RandomSeed = rs

    # tetrahedralize grid
    tetrah = simple.Tetrahedralize(Input=ir)

    # vtkUnstructuredGrid (TTK)
    simple.SaveData(f"{out}.vtu", proxy=tetrah)
    # Dipha Explicit Complex (Dipha)
    simple.SaveData(f"{out}.dipha", proxy=tetrah)


def main():
    DIR = "small_rnd"
    try:
        os.mkdir(DIR)
    except FileExistsError:
        pass
    ds = f"{DIR}/rnd"
    diag = f"{ds}_diag"
    extent = (5, 5, 5)
    failing = []
    for i in range(0, 500):
        print(i)
        generate_random(extent, ds, i)
        # call TTK
        subprocess.run(
            ["ttkPersistenceDiagramCmd"]
            + ["-i", f"{ds}.vtu"]
            + ["-a", "ImageFile_Order"]
            + ["-B", "2"],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        os.rename("output_port_0.vtu", f"{diag}.vtu")
        # call Dipha
        subprocess.run(
            ["build_dipha/dipha", f"{ds}.dipha", f"{diag}.dipha"],
            check=True,
        )
        res = compare_diags.main(f"{diag}.dipha", f"{diag}.vtu", True)
        if res.get("saddle-saddle", 0.0) != 0.0 or res.get("saddle-max", 0.0) != 0.0:
            shutil.copyfile(f"{ds}.vtu", f"{ds}{i}.vtu")
            time.sleep(5)
            failing.append(i)

    print(failing)


if __name__ == "__main__":
    main()

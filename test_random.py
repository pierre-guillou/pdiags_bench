import os
import time
import subprocess

from paraview import simple

import compare_diags
import gen_random


def generate_explicit(inp, out, rs):
    # read random.vti
    rand = simple.XMLImageDataReader(FileName=inp)
    # compute order field
    arrprec = simple.TTKArrayPreconditioning(Input=rand)
    arrprec.PointDataArrays = ["ImageFile"]
    # trash input scalar field, save order field
    pa = simple.PassArrays(Input=arrprec)
    pa.PointDataArrays = ["ImageFile_Order"]
    # randomize scalar field?
    ir = simple.TTKIdentifierRandomizer(Input=pa)
    ir.ScalarField = ["POINTS", "ImageFile_Order"]
    ir.RandomSeed = rs
    # tetrahedralize grid
    tetrah = simple.Tetrahedralize(Input=ir)

    # vtkUnstructuredGrid (TTK)
    simple.SaveData(f"{out}.vtu", proxy=tetrah)
    # Dipha Explicit Complex (Dipha)
    simple.SaveData(f"{out}.dipha", proxy=tetrah)
    # TTK Simplicial Complex (Gudhi, Dionysus, Ripser)
    simple.SaveData(f"{out}.tsc", proxy=tetrah)


def main(gen_rnd=False):
    fname = "random_order_sfnorm_expl"
    for i in range(0, 8):
        ds = f"datasets/{fname}"
        if gen_rnd:
            print(i)
            gen_random.main(4, "random", ".")
            generate_explicit("random.vti", ds, i)
        # call TTK
        subprocess.run(
            ["ttkPersistenceDiagramCmd"]
            + ["-i", f"{ds}.vtu"]
            + ["-a", "ImageFile_Order"]
            + ["-B", "2"],
            check=True,
        )
        os.rename("output_port_0.vtu", "random_diag.vtu")
        # call Dipha
        subprocess.run(
            ["build_dipha/dipha", f"{ds}.dipha", "random_diag.dipha"],
            check=True,
        )
        compare_diags.main("random_diag.vtu", "random_diag.dipha", True)
        if not gen_rnd:
            return
        time.sleep(2)


if __name__ == "__main__":
    main()

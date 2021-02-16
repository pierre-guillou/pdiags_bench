import time

from paraview import simple

import compare_diags
import gen_random
import main as compute_diags


def generate_explicit(inp, out, rs):
    # read random.vti
    rand = simple.XMLImageDataReader(FileName=inp)
    # compute order field
    arrprec = simple.TTKArrayPreconditioning(Input=rand)
    arrprec.PointDataArrays = ["RandomPointScalars"]
    # trash input scalar field, save order field
    pa = simple.PassArrays(Input=arrprec)
    pa.PointDataArrays = ["RandomPointScalars_Order"]
    # randomize scalar field?
    ir = simple.TTKIdentifierRandomizer(Input=pa)
    ir.ScalarField = ["POINTS", "RandomPointScalars_Order"]
    ir.RandomSeed = rs
    # tetrahedralize grid
    tetrah = simple.Tetrahedralize(Input=ir)

    # vtkUnstructuredGrid (TTK)
    simple.SaveData(out + ".vtu", proxy=tetrah)
    # Dipha Explicit Complex (Dipha)
    simple.SaveData(out + ".dipha", proxy=tetrah)


def main():
    fname = "random_order_sfnorm_expl"
    for i in range(0, 8):
        print(i)
        gen_random.main(4, "rand")
        ds = "datasets/" + fname
        generate_explicit("random.vti", ds, i)
        return
        tm = dict()
        tm[fname.split("/")[-1]] = dict()
        compute_diags.compute_ttk(ds + ".vtu", "ttkPersistenceDiagramCmd", tm)
        compute_diags.compute_dipha(ds + ".dipha", "build_dipha/dipha", tm)
        diag = "diagrams/" + fname
        compare_diags.main(diag + ".vtu", diag + ".dipha", True)
        time.sleep(2)


if __name__ == "__main__":
    main()

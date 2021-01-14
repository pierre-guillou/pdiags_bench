from paraview import simple

import compare_diags
import gen_random
import main as compute_diags


def generate_explicit(inp, out):
    # read random.vti
    rand = simple.XMLImageDataReader(FileName=inp)
    # compute order field
    arrprec = simple.TTKArrayPreconditioning(Input=rand)
    arrprec.PointDataArrays = ["RandomPointScalars"]
    # trash input scalar field, save order field
    pa = simple.PassArrays(Input=arrprec)
    pa.PointDataArrays = ["RandomPointScalars_Order"]
    # tetrahedralize grid
    tetrah = simple.Tetrahedralize(Input=pa)

    # vtkUnstructuredGrid (TTK)
    simple.SaveData(out + ".vtu", proxy=tetrah)
    # Dipha Explicit Complex (Dipha)
    simple.SaveData(out + ".dipha", proxy=tetrah)


def main():
    fname = "random_order_sfnorm_expl"
    for i in range(8, 50):
        gen_random.main(i, "rand")
        ds = "datasets/" + fname
        generate_explicit("random.vti", ds)
        tm = dict()
        tm[fname.split("/")[-1]] = dict()
        compute_diags.compute_ttk(ds + ".vtu", "ttkPersistenceDiagramCmd", tm)
        compute_diags.compute_dipha(ds + ".dipha", "build_dipha/dipha", tm)
        diag = "diagrams/" + fname
        compare_diags.main(diag + ".vtu", diag + ".dipha")


if __name__ == "__main__":
    main()

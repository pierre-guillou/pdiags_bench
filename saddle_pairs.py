import argparse
import multiprocessing
import os
import subprocess

import numpy as np
from paraview import servermanager, simple
from paraview.vtk.numpy_interface import dataset_adapter as dsa

import compare_diags

DIR = "rndsmoo"


def gen_randoms(seed):
    fug = simple.FastUniformGrid()
    fug.WholeExtent = [0, 64, 0, 64, 0, 64]

    tetrah = simple.Tetrahedralize(Input=fug)

    ra = simple.RandomAttributes(Input=tetrah)
    ra.DataType = "Int"
    ra.GeneratePointScalars = 1
    ra.GenerateCellVectors = 0

    vtk_ra = servermanager.Fetch(ra)
    data = dsa.WrapDataObject(vtk_ra)
    array = data.PointData["RandomPointScalars"]
    gen = np.random.default_rng(seed)
    gen.shuffle(array)

    smoo = simple.TTKScalarFieldSmoother(Input=ra)
    smoo.ScalarField = ["POINTS", "RandomPointScalars"]
    smoo.IterationNumber = 55
    simp = simple.TTKTopologicalSimplificationByPersistence(Input=smoo)
    simp.InputArray = ["POINTS", "RandomPointScalars"]
    simp.PersistenceThreshold = 200

    pa = simple.PassArrays(Input=simp)
    pa.PointDataArrays = ["RandomPointScalars_Order"]

    rgi = simple.RemoveGhostInformation(Input=pa)

    simple.SaveData(f"{DIR}/test{seed}.vtu", Input=rgi)


def ds_dipha(seed):
    vtu = simple.XMLUnstructuredGridReader(FileName=f"{DIR}/test{seed}.vtu")
    simple.SaveData(f"{DIR}/test{seed}.dipha", Input=vtu)


def ds_tsc(seed):
    vtu = simple.XMLUnstructuredGridReader(FileName=f"{DIR}/test{seed}.vtu")
    simple.SaveData(f"{DIR}/test{seed}.tsc", Input=vtu)


def compute_dipha_diag(seed):
    print(f"Calling Dipha on {DIR}/test{seed}.dipha...")
    subprocess.check_call(
        [
            "mpirun",
            "build_dipha/dipha",
            f"{DIR}/test{seed}.dipha",
            f"{DIR}/out{seed}.dipha",
        ]
    )


def compute_gudhi_diag(seed):
    print(f"Calling Gudhi on {DIR}/test{seed}.gudhi...")
    subprocess.check_call(
        ["poetry", "run"]
        + ["python", "dionysus_gudhi_persistence.py"]
        + ["-b", "gudhi"]
        + ["-i", f"{DIR}/test{seed}.tsc"]
        + ["-o", f"{DIR}/out{seed}.gudhi"]
    )


def compute_ttk_diag(seed):
    reader = simple.XMLUnstructuredGridReader(FileName=f"{DIR}/test{seed}.vtu")

    pdiag = simple.TTKPersistenceDiagram(Input=reader)
    pdiag.ScalarField = ["POINTS", "RandomPointScalars_Order"]
    pdiag.Backend = "DMT Pairs"
    pdiag.IgnoreBoundary = False
    pdiag.DebugLevel = 4

    simple.SaveData(f"{DIR}/out{seed}.vtu", Input=pdiag)


def compare(seed):
    res = compare_diags.main(
        f"{DIR}/out{seed}.dipha", f"{DIR}/out{seed}.vtu", True, True
    )
    if any(v != 0.0 for v in res.values()):
        print(f"Differences for seed {seed}")
        return False
    return True


def main(prepare=True, gen_dipha=False, gen_ttk=False, comp_diags=False):
    try:
        os.mkdir(DIR)
    except FileExistsError:
        pass

    diff = []

    # [71, 105, 201, 417, 470]

    for seed in range(500):
        print(f"Seed {seed}")
        if prepare:
            gen_randoms(seed)
            # ds_dipha(seed)
            ds_tsc(seed)
        if gen_dipha:
            # compute_dipha_diag(seed)
            compute_gudhi_diag(seed)
        if gen_ttk:
            p = multiprocessing.Process(target=compute_ttk_diag, args=(seed,))
            p.start()
            p.join()
        if comp_diags:
            ident = compare(seed)
            if not ident:
                diff.append(seed)

    if len(diff) > 0:
        print(f"Differences for #{len(diff)} seeds: {diff}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate & compare smoothed randoms")
    parser.add_argument(
        "-0",
        "--prepare",
        help="Generate VTUs & Dipha datasets",
        action="store_true",
    )
    parser.add_argument(
        "-1",
        "--compute_dipha",
        help="Compute Dipha diagrams",
        action="store_true",
    )
    parser.add_argument(
        "-2",
        "--compute_ttk",
        help="Compute TTK diagrams",
        action="store_true",
    )
    parser.add_argument(
        "-3",
        "--compare_diags",
        help="Compare Dipha & TTK diagrams",
        action="store_true",
    )
    args = parser.parse_args()
    main(args.prepare, args.compute_dipha, args.compute_ttk, args.compare_diags)
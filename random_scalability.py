import os
import pathlib
import subprocess

from paraview import simple


def gen_random(size, destdir):

    file = pathlib.Path(f"{destdir}/random_{size}x{size}x{size}_order_expl.vtu")

    if file.exists():
        print(f"File {file} already exists!")
        return file

    fug = simple.FastUniformGrid()
    fug.WholeExtent = [0, size - 1, 0, size - 1, 0, size - 1]

    sfname = "RandomPointScalars"

    sf = simple.RandomAttributes(Input=fug)
    sf.DataType = "Float"
    sf.ComponentRange = [0.0, 1.0]
    sf.GeneratePointScalars = 1
    sf.GenerateCellVectors = 0

    # rename scalar field to "ImageFile" (and convert it to float)
    calc = simple.Calculator(Input=sf)
    calc.Function = sfname
    calc.ResultArrayType = "Float"
    calc.ResultArrayName = "ImageFile"

    # compute order field
    arrprec = simple.TTKArrayPreconditioning(Input=calc)
    arrprec.PointDataArrays = ["ImageFile"]

    # trash input scalar field, save order field
    pa = simple.PassArrays(Input=arrprec)
    pa.PointDataArrays = ["ImageFile_Order"]

    # tetrahedralize grid
    tetrah = simple.Tetrahedralize(Input=pa)

    # remove vtkGhostType arrays (only applies on vtu & vtp)
    rgi = simple.RemoveGhostInformation(Input=tetrah)

    simple.SaveData(str(file), Input=rgi)
    return file


def compute_persistence(file):
    cmd = (
        ["build_dirs/install_paraview_v5.10.1/bin/ttkPersistenceDiagramCmd"]
        + ["-i", file]
        + ["-d", "4"]
        + ["-a", "ImageFile_Order"]
        + ["-B", "2"]
    )
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    ) as proc:
        return (proc.stdout.read(), proc.stderr.read())


def store_log(log, ds_name, app, nthreads=None):
    thrs = f".{nthreads}T" if nthreads is not None else ""
    file_name = f"logs/{ds_name}.{app}{thrs}.log"
    with open(file_name, "w") as dst:
        dst.write(log)


def main():
    destdir = "random_scalability"
    try:
        os.mkdir(destdir)
    except FileExistsError:
        pass

    for size in [8, 16, 32, 64, 128, 256]:
        file = gen_random(size, destdir)
        out, _ = compute_persistence(file)
        store_log(out, file.stem, "DiscreteMorseSandwich", 16)


if __name__ == "__main__":
    main()

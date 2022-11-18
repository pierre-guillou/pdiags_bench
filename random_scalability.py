import json
import os
import pathlib
import re
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


def escape_ansi_chars(txt):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", txt)


regexp_map = {
    "nverts": r"\[DiscreteGradient\] #Vertices.*: (\d*)",
    "nedges": r"\[DiscreteGradient\] #Edges.*: (\d*)",
    "ntri": r"\[DiscreteGradient\] #Triangles.*: (\d*)",
    "ntetra": r"\[DiscreteGradient\] #Tetras.*: (\d*)",
    "dg_mem": r"\[DiscreteGradient.*\] Initialized discrete gradient memory.*\[(\d+\.\d+|\d+)s",
    "dg": r"\[DiscreteGradient.*\] Built discrete gradient.*\[(\d+\.\d+|\d+)s",
    "alloc": r"\[DiscreteMorseSandwich.*\] Memory allocations.*\[(\d+\.\d+|\d+)s",
    "sort": r"\[DiscreteMorseSandwich.*\] Extracted & sorted critical cells.*\[(\d+\.\d+|\d+)s",
    "minSad": r"\[DiscreteMorseSandwich.*\] Computed .* min-saddle pairs.*\[(\d+\.\d+|\d+)s",
    "sadMax": r"\[DiscreteMorseSandwich.*\] Computed .* saddle-max pairs.*\[(\d+\.\d+|\d+)s",
    "sadSad": r"\[DiscreteMorseSandwich.*\] Computed .* saddle-saddle pairs.*\[(\d+\.\d+|\d+)s",
    "pairs": r"\[DiscreteMorseSandwich.*\] Computed .* persistence pairs.*\[(\d+\.\d+|\d+)s",
    "total": r"\[PersistenceDiagram.*\] Complete.*\[(\d+\.\d+|\d+)s",
}


def ttk_time(ttk_output, regexp):
    try:
        return float(re.search(regexp, ttk_output, re.MULTILINE).group(1))
    except AttributeError:
        return 0.0


def parse_log(log):
    res = {}
    ttk_output = escape_ansi_chars(log)
    for k, v in regexp_map.items():
        res[k] = ttk_time(ttk_output, v)
    res["D1"] = res.pop("sadSad")
    res["D0+D2"] = res["minSad"] + res["sadMax"]
    return res


def process():
    destdir = "random_scalability"
    try:
        os.mkdir(destdir)
    except FileExistsError:
        pass

    res = {}

    for size in [8, 16, 32, 64, 128, 256]:
        file = gen_random(size, destdir)
        out, _ = compute_persistence(file)
        res[file.stem] = parse_log(out)

    with open("random_scalability.json", "w") as dst:
        json.dump(res, dst, indent=4)


def gen_table():
    with open("random_scalability.json") as src:
        data = json.load(src)

    print(json.dumps(data, indent=4))


def main():
    # process()
    gen_table()


if __name__ == "__main__":
    main()

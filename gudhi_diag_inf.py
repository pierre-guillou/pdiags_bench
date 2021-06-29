import pathlib
import re


def replace_inf(diag):
    with open(diag, "r") as src:
        pairs = src.read()
    patt = re.compile(r".*_(\d+)x(\d+)x(\d+)_.*")
    dims = re.match(patt, diag.stem).groups()
    dims = [int(d) for d in dims]
    max_order = dims[0] * dims[1] * dims[2]
    out_pairs = list()
    for line in pairs.split("\n"):
        if "inf" in line:
            line = line.replace("inf", str(max_order))
        out_pairs.append(line)
    with open(diag, "w") as dst:
        dst.write("\n".join(out_pairs))


def main():
    """Read a Persistence Diagram in the Gudhi format and replace the
    "inf" value with the maximum order extracted from the dataset
    dimensions from the diagram file name.
    """
    p = pathlib.Path("diagrams")
    for diag in sorted(p.glob("*.gudhi")):
        replace_inf(diag)
        print(f"Post-processed {diag}")


if __name__ == "__main__":
    main()

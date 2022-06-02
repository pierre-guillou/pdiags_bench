import pathlib
import re


def replace_inf(diag):
    with open(diag, "r") as src:
        pairs = src.read()
    patt = re.compile(r".*_(\d+)x(\d+)x(\d+)_.*")
    dims = re.match(patt, diag.stem).groups()
    dims = [int(d) for d in dims]
    max_order = dims[0] * dims[1] * dims[2] - 1
    out_pairs = list()
    found = False
    for line in pairs.split("\n"):
        line = line.lower()
        if "inf" in line:
            line = line.replace("inf", str(max_order))
            found = True
        out_pairs.append(line)
    if not found:
        # skip rewrite part if no "inf" in file
        return found
    with open(diag, "w") as dst:
        dst.write("\n".join(out_pairs))
    return found


def main():
    """Read a Persistence Diagram in the Gudhi format and replace the
    "inf" value with the maximum order extracted from the dataset
    dimensions from the diagram file name.
    """
    p = pathlib.Path("diagrams")
    for diag in sorted(p.glob("*.gudhi")):
        found = replace_inf(diag)
        if found:
            print(f"Post-processed {diag}")


if __name__ == "__main__":
    main()

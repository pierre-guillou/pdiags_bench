import argparse
import json
import os
import subprocess


def add_standalone(fname, res=list()):
    res.append(r"\documentclass{standalone}")
    res.append("")
    res.append(r"\usepackage{booktabs}")
    res.append("")
    res.append(r"\begin{document}")
    res.append("")

    gen_table(fname, res)

    res.append("")
    res.append(r"\end{document}")
    return res


def find_min_time(vals, cols):
    times = []
    for i, val in enumerate(vals):
        if "#" in cols[i]:
            continue
        try:
            times.append((i, float(val)))
        except ValueError:
            pass
    return min(times, key=lambda x: x[1])


def gen_table(fname, res=list()):
    with open(fname, "r") as src:
        data = json.load(src)
    # use dicts to get an ordered sets
    lines = {}
    cols = {}
    for ds, vals in data.items():
        lines["_".join(ds.split("_")[:-2])] = None
        for item in vals:
            cols[item] = None
    cols = ["Dataset"] + list(cols)
    # escape "#" chars
    cols_escape = []
    for name in cols:
        if "#" in name:
            name = "\\" + name
        cols_escape.append(name)
    cols_dict = {name: i for i, name in enumerate(cols)}
    cols = cols_escape
    lines = list(lines)
    res.append(r"\begin{tabular}[ht]{l" + "c" * (len(cols) - 1) + "}")
    res.append(r"  \toprule")
    res.append("  " + " & ".join(cols) + r" \\")
    res.append(r"  \midrule")
    res.append("")
    for ds in lines:
        ds_name = r"\_".join(ds.split("_")[:-2])
        curr = [ds_name] * len(cols)
        for it, val in data[ds + "_order_expl"].items():
            curr[cols_dict[it]] = str(val)
        for it, val in data[ds + "_order_impl"].items():
            if "#" not in it:
                curr[cols_dict[it]] = str(val)
        # consistency check
        for i, val in enumerate(curr):
            if i != 0 and val == curr[0]:
                curr[i] = r"+30min"
        # find the min execution time and put it in bold
        m = find_min_time(curr, cols)
        curr[m[0]] = r"\textbf{" + curr[m[0]] + r"}"
        # append current line
        res.append("  " + " & ".join(curr) + r" \\")
    res.append(r"  \bottomrule")
    res.append(r"\end{tabular}")
    return res


def main(fname, standalone=False, generate=False):
    res = list()
    if standalone or generate:
        res = add_standalone(fname, res)
    else:
        res = gen_table(fname, res)
    if generate:
        with open("tmp.tex", "w") as dst:
            dst.write("\n".join(res))
        cmd = ["latexmk", "-pdf", "tmp.tex"]
        subprocess.run(cmd)
        cmd = ["latexmk", "-c"]
        subprocess.run(cmd)
        os.remove("tmp.tex")
        os.rename("tmp.pdf", fname + ".pdf")
    else:
        print("\n".join(res))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a LaTeX table from JSON results"
    )
    parser.add_argument("JSON_File", type=str, help="Path to JSON results file")
    parser.add_argument(
        "-s",
        "--standalone",
        action="store_true",
        help="Embed output in standalone LaTeX file",
    )
    parser.add_argument(
        "-g",
        "--generate",
        action="store_true",
        help="Generate a standalone PDF",
    )
    args = parser.parse_args()
    main(args.JSON_File, args.standalone, args.generate)

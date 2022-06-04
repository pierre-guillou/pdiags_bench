import argparse
import json
import os
import subprocess


def add_standalone(fname, res, simpl_cpx):
    if not res:
        res = []
    res.append(r"\documentclass{standalone}")
    res.append("")
    res.append(r"\usepackage{booktabs}")
    res.append(r"\usepackage[table]{xcolor}")
    res.append("")
    res.append(r"\begin{document}")
    res.append("")

    gen_table(fname, res, simpl_cpx)

    res.append("")
    res.append(r"\end{document}")
    return res


def sort_times(vals, cols):
    times = []
    for i, val in enumerate(vals):
        if "#" in cols[i]:
            continue
        try:
            times.append((i, float(val)))
        except ValueError:
            pass
    return sorted(times, key=lambda x: x[1])


def gen_table(fname, res, simplicial=True):
    if not res:
        res = []
    with open(fname, "r") as src:
        data = json.load(src)
    # use dicts to get an ordered sets
    lines = []
    cols = {}
    # only keep simplicial vs cubical results
    data = {
        ds: vals
        for ds, vals in data.items()
        if (simplicial and "expl" in ds) or (not simplicial and "impl" in ds)
    }
    for ds, vals in data.items():
        lines.append(ds)
        for item in vals:
            cols[item] = None
    cols = ["Dataset"] + list(cols)
    cols_dict = {name: i for i, name in enumerate(cols)}
    # escape "#" chars
    cols = [name.replace("#", "\\#") for name in cols]
    res.append(r"\begin{tabular}[ht]{l" + "c" * (len(cols) - 1) + "}")
    res.append(r"  \toprule")
    res.append("  " + " & ".join(cols) + r" \\")
    res.append(r"  \midrule")
    res.append("")
    for ds in lines:
        ds_name = r"\_".join(ds.split("_")[:-3])
        curr = [ds_name] * len(cols)
        for it, val in data[ds].items():
            if isinstance(val, dict):
                if "para" in val.keys():
                    val = val["para"]["pers"]
                elif "seq" in val.keys():
                    val = val["seq"]["pers"]
                elif "timeout" in val.keys():
                    if val["timeout"] > 60 :
                        timeout = int(val["timeout"] / 60)
                        timeout = f"+{timeout}min"
                    else:
                        timeout = val["timeout"]
                        timeout = f"+{timeout}s"
                    val = r"\cellcolor{lightgray}%s" % timeout
                else:
                    val = r"\cellcolor{lightgray}{Err.}"
            curr[cols_dict[it]] = str(val)
        # consistency check
        for i, val in enumerate(curr):
            if i != 0 and val == curr[0]:
                curr[i] = r"\cellcolor{lightgray}{No res}"
        # sort times in increasing order
        colors = ["green", "lime", "yellow", "orange", "brown", "red", "purple", "violet"]
        stimes = sort_times(curr, cols)
        for t, c in zip(stimes, colors):
            curr[t[0]] = r"\cellcolor{" + c + "}" + curr[t[0]]
        # append current line
        res.append("  " + " & ".join(curr) + r" \\")
    res.append(r"  \bottomrule")
    res.append(r"\end{tabular}")
    return res


def main(fname, standalone=False, generate=False):
    for cpx in ["simplicial", "cubical"]:
        res = []
        if standalone or generate:
            res = add_standalone(fname, res, cpx == "simplicial")
        else:
            res = gen_table(fname, res, cpx == "simplicial")
        if generate:
            with open("tmp.tex", "w") as dst:
                dst.write("\n".join(res))
            cmd = ["latexmk", "-pdf", "tmp.tex"]
            subprocess.run(cmd, check=False)
            cmd = ["latexmk", "-c"]
            subprocess.run(cmd, check=False)
            os.remove("tmp.tex")
            os.rename("tmp.pdf", f"{fname}_{cpx}.pdf")
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

import argparse
import json


def main(fname, standalone=False):
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
    res = []
    if standalone:
        res.append(r"\documentclass{standalone}")
        res.append("")
        res.append(r"\usepackage{booktabs}")
        res.append("")
        res.append(r"\begin{document}")
        res.append("")
    res.append(r"\begin{tabular}[ht]{l" + "c" * (len(cols) - 1) + "}")
    res.append(r"  \toprule")
    res.append("  " + " & ".join(cols) + r" \\")
    res.append(r"  \midrule")
    res.append("")
    for ds in lines:
        curr = ["\\_".join(ds.split("_"))] * len(cols)
        for it, val in data[ds + "_order_expl"].items():
            curr[cols_dict[it]] = str(val)
        for it, val in data[ds + "_order_impl"].items():
            if "#" not in it:
                curr[cols_dict[it]] = str(val)
        # consistency check
        for i, val in enumerate(curr):
            if i != 0 and val == curr[0]:
                curr[i] = "Err."
        res.append("  " + " & ".join(curr) + r" \\")
    res.append(r"  \bottomrule")
    res.append(r"\end{tabular}")
    if standalone:
        res.append("")
        res.append(r"\end{document}")
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
    args = parser.parse_args()
    main(args.JSON_File, args.standalone)

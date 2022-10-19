import json
import os
import pathlib
import re


def escape_ansi_chars(txt):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", txt)


regexp_map = {
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
    return float(re.search(regexp, ttk_output, re.MULTILINE).group(1))


def parse_logs():
    p = pathlib.Path(os.path.realpath(__file__)).parents[1] / "logs"
    res = {}
    for log in sorted(p.glob("*DiscreteMorseSandwich*log")):
        ds, _, nt = log.stem.split(".")
        nt = int(nt[:-1])
        dsname = "_".join(ds.split("_")[:-2])
        if dsname not in res:
            res[dsname] = []
        res[dsname].append({"num_threads": nt})
        with open(log, "r") as src:
            ttk_output = escape_ansi_chars(src.read())
            for k, v in regexp_map.items():
                res[dsname][-1][k] = ttk_time(ttk_output, v)

    return res


def print_tex_array(data):
    # print in LaTeX array format
    arrays = ["dg", "minSad", "sadMax", "sadSad", "total"]
    arrs = " & ".join(arrays)
    print(rf"Data-set & size & {arrs} & {arrs} \\")
    for k, v in data.items():
        dsname = "_".join(k.split("_")[:-1])
        size = k.split("_")[-1]
        vals = []
        for entry in v:
            for kk, vv in entry.items():
                if kk in arrays:
                    vals.append(str(vv))
        vals = " & ".join(vals)
        print(rf"{dsname} & {size} & {vals} \\")


def main():
    res = parse_logs()

    # print in JSON format
    print(json.dumps(res, indent=4))

    print_tex_array(res)


if __name__ == "__main__":
    main()

import json
import os
import pathlib
import re
import statistics


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
    try:
        return float(re.search(regexp, ttk_output, re.MULTILINE).group(1))
    except AttributeError:
        return 0.0


def parse_logs():
    p = pathlib.Path(os.path.realpath(__file__)).parents[1] / "logs"
    res = {}
    for log in sorted(p.glob("*DiscreteMorseSandwich*log")):
        ds, _, nt = log.stem.split(".")
        nt = int(nt[:-1])
        dsname = "_".join(ds.split("_")[:-2])
        triangl = ds.split("_")[-1]
        if dsname not in res:
            res[dsname] = []
        res[dsname].append({"num_threads": nt, "triangl": triangl})
        with open(log, "r") as src:
            ttk_output = escape_ansi_chars(src.read())
            for k, v in regexp_map.items():
                res[dsname][-1][k] = ttk_time(ttk_output, v)

    return res


def compute_stats(data, seq, expl):
    res = {"dg": 0.0, "minSad": 0.0, "sadMax": 0.0, "sadSad": 0.0}
    if not seq and expl:
        sid = 0
    elif seq and expl:
        sid = 1
    elif not seq and not expl:
        sid = 2
    elif seq and not expl:
        sid = 3

    total = []
    size = list(data)[0].split("_")[-1]
    if size.endswith("x1x1"):
        dim = "1D"
    elif size.endswith("x1"):
        dim = "2D"
    else:
        dim = "3D"

    for v in data.values():
        for kk, vv in v[sid].items():
            if kk in res:
                res[kk] += vv
        total.append(v[sid]["total"])

    for k, v in res.items():
        res[k] = v / len(data)
    res |= {
        "total_mean": statistics.mean(total),
        "total_min": min(total),
        "total_max": max(total),
        "total_stdev": statistics.stdev(total),
        "dim": dim,
        "sequential": seq,
        "explicit": expl,
    }
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

    # print_tex_array(res)

    for seq in [True, False]:
        for expl in [True, False]:
            stats = compute_stats(res, seq, expl)
            print(json.dumps(stats, indent=4))


if __name__ == "__main__":
    main()

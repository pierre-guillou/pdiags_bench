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
            res[dsname][-1]["D1"] = res[dsname][-1].pop("sadSad")
            res[dsname][-1]["D0+D2"] = (
                res[dsname][-1]["minSad"] + res[dsname][-1]["sadMax"]
            )

    return res


def compute_stats(data, seq, expl, dim):
    res = {"dg": [], "D0+D2": [], "D1": [], "total": []}

    def has_correct_dim(ds):
        size = ds.split("_")[-1]
        if dim == "3D":
            return not size.endswith("x1")
        if dim == "2D":
            return size.endswith("x1") and not size.endswith("x1x1")
        if dim == "1D":
            return size.endswith("x1x1")
        return False

    def has_correct_threads(val):
        if seq:
            return val["num_threads"] == 1
        return val["num_threads"] == 16

    def has_correct_triangl(val):
        if expl:
            return val["triangl"] == "expl"
        return val["triangl"] == "impl"

    data_filtr = {}
    for k, v in data.items():
        if not has_correct_dim(k):
            continue
        for el in v:
            if not has_correct_threads(el):
                continue
            if not has_correct_triangl(el):
                continue
            data_filtr[k] = el

    for v in data_filtr.values():
        for kk, vv in v.items():
            if kk in res:
                res[kk].append(vv)

    for k, v in res.items():
        res[k] = {
            "mean": statistics.mean(v),
            "min": min(v),
            "max": max(v),
            "stdev": statistics.stdev(v),
        }

    res |= {
        "dim": dim,
        "sequential": seq,
        "explicit": expl,
    }

    return res


def print_tex_array(data):
    # print in LaTeX array format
    arrays = ["dg", "D0+D2", "D1", "total"]
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

    stats = []
    for dim in ["1D", "2D", "3D"]:
        for seq in [True, False]:
            for expl in [True, False]:
                # no implicit grids in 1D
                if dim == "1D" and not expl:
                    continue

                stats.append(compute_stats(res, seq, expl, dim))
    print(json.dumps(stats, indent=4))


if __name__ == "__main__":
    main()

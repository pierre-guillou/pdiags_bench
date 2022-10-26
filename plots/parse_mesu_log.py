import json
import re
import sys

import plots_utils


def escape_ansi_chars(txt):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", txt)


def ttk_compute_time(ttk_output):
    ttk_output = escape_ansi_chars(ttk_output)
    time_re = r"\[PersistenceDiagram\] Complete.*\[(\d+\.\d+|\d+)s"
    cpt_time = float(re.search(time_re, ttk_output, re.MULTILINE).group(1))
    overhead = ttk_overhead_time(ttk_output)
    return cpt_time - overhead


def ttk_overhead_time(ttk_output):
    time_re = r"\[DiscreteGradient\] Memory allocations.*\[(\d+\.\d+|\d+)s"
    try:
        return float(re.search(time_re, ttk_output, re.MULTILINE).group(1))
    except AttributeError:
        return 0.0


def ttk_prec_time(ttk_output):
    ttk_output = escape_ansi_chars(ttk_output)
    prec_re = r"\[PersistenceDiagram\] Precondition triangulation.*\[(\d+\.\d+|\d+)s"
    prec_time = float(re.search(prec_re, ttk_output, re.MULTILINE).group(1))
    return prec_time


def dipha_compute_time(dipha_output):
    run_pat = r"^Overall running time.*\n(\d+.\d+|\d+)$"
    run_time = re.search(run_pat, dipha_output, re.MULTILINE).group(1)
    run_time = float(run_time)
    read_pat = r"^ *(\d+.\d+|\d+)s.*complex.load_binary.*$"
    read_time = re.search(read_pat, dipha_output, re.MULTILINE).group(1)
    read_time = float(read_time)
    write_pat = r"^ *(\d+.\d+|\d+)s.*save_persistence_diagram.*$"
    write_time = re.search(write_pat, dipha_output, re.MULTILINE).group(1)
    write_time = float(write_time)
    prec = round(read_time + write_time, 3)
    pers = round(run_time - prec, 3)
    return pers


def phat_compute_time(output):
    pers_pat = r"Computing persistence pairs took (\d+.\d+|\d+)s"
    pers = re.search(pers_pat, output, re.MULTILINE).group(1)
    return round(float(pers), 3)


def persistenceCycles_compute_time(output):
    grad_pat = r"Gradient computed in (\d+.\d+|\d+) seconds"
    grad = re.search(grad_pat, output, re.MULTILINE).group(1)
    pers_pat = (
        r"Persistent homology computed in "
        + r"[+-]?(\d+([.]\d*)?(e[+-]?\d+)?|[.]\d+(e[+-]?\d+)?) seconds"
    )
    pers = re.search(pers_pat, output, re.MULTILINE).group(1)
    return round(float(grad) + float(pers), 3)


def read_file(file):
    with open(file) as src:
        return src.readlines()


def split_sections(lines):
    pat = r"^.*Processing .*\/(.*)\..* with (.*) with (\d*).*...$"
    delimiters = []
    sections = []
    for i, line in enumerate(lines):
        if "Processing" in line:
            delimiters.append(i)
            res = re.search(pat, line)
            sections.append(res.groups())
    delimiters.append(len(lines))
    # sections: [0] = dataset, [1] = backend, [2] = #threads
    return sections, delimiters


def parse_sections(lines, sections, delimiters):
    dispatch = {
        "DiscreteMorseSandwich": ttk_compute_time,
        "TTK-FTM": ttk_compute_time,
        "Dipha": dipha_compute_time,
        "PHAT": phat_compute_time,
        "PersistenceCycles": persistenceCycles_compute_time,
    }

    res = {k: {sec[0]: {} for sec in sections} for k in dispatch}
    for i, sec in enumerate(sections):
        seclog = "".join(lines[slice(delimiters[i], delimiters[i + 1])])
        dataset, backend, nthreads = sec
        try:
            res[backend][dataset][int(nthreads)] = {
                "pers": dispatch[backend](seclog),
                "#threads": int(nthreads),
            }
        except AttributeError:
            # print(seclog)
            # input()
            continue

    return res


def aggregate_backend_nthreads(res, dim=3):
    n_simplices = plots_utils.compute_n_simplices(dim - 1)
    # compute mean times per backend & #thread
    aggr = {}
    for bk, bk_data in res.items():
        aggr[bk] = {}
        for nthreads in [1, 2, 4, 8, 16, 32, 64, 96, 128]:
            i = 0
            time = 0.0
            speed = 0.0
            for perf in bk_data.values():
                if nthreads in perf:
                    i += 1
                    time += perf[nthreads]["pers"]
                    speed += n_simplices / perf[nthreads]["pers"]
            if i > 0:
                mtime = time / i
                mspeed = speed / i
                aggr[bk][nthreads] = mtime
                print(
                    f"{bk} {nthreads} threads ({i} datasets): {mtime:.3f} s, {mspeed:.1f} #simplices/s"
                )

    return aggr


def plot_aggregated_data(aggr):
    legend_pos = r"""\node at (plots c2r1.east)[inner sep=0pt, xshift=12ex]
{\pgfplotslegendfromname{grouplegend}};"""

    backends_legend = {
        "DiscreteMorseSandwich": "curve1",
        "Dipha": "curve2",
        "PHAT": "curve3",
        "PersistenceCycles": "curve4",
        "TTK-FTM": "curve5",
    }

    plot = []

    for i, data in enumerate(aggr):
        dim = i + 2

        plot.append(
            "\n"
            + r"\nextgroupplot[legend to name=grouplegend, ymode=log, "
            + ("ylabel=Computation speed (simplices/second)," if dim == 2 else "")
            + "xtick=data, xticklabels = {1,,,,, 32, 64,, 128},"
            + "]"
        )

        for bk, legend in backends_legend.items():
            if "FTM" in bk and dim == 3:
                plot.append(rf"\addlegendimage{{{legend}}}")
                plot.append(rf"\addlegendentry{{{bk}}}")
                continue
            coords = [r"\addplot[" + legend + "] coordinates {"]
            for nthreads, val in data[bk].items():
                coords.append(f"({nthreads}, {val})")
            coords.append("};")
            plot.append(" ".join(coords))
            plot.append(r"\addlegendentry{" + bk + "}")

    plots_utils.output_tex_file(
        plot,
        "plot_mesu_expl",
        False,
        False,
        r"width=.35\linewidth",
        legend_pos,
    )

    return plot


def main():
    aggr = []

    for file in ["mesu_2D_1-128.log", "mesu_3D_1-128.log"]:

        print(file)
        lines = read_file(file)
        sections, delimiters = split_sections(lines)
        res = parse_sections(lines, sections, delimiters)

        # json.dump(res, sys.stdout, indent=4)

        aggr.append(aggregate_backend_nthreads(res))

    plot_aggregated_data(aggr)


if __name__ == "__main__":
    main()

import functools
import json
import subprocess
import sys

# holds function pointers that generate CSV files
CSV_GENS = []


def register_csv_gen(csv_gen):
    """Register CSV generator functions into the global CSV_GENS list"""

    def _csv_gen_wrapped(gen_files=False):
        """Wrapper around CSV generator function: output CSV to stdout or to
        function_name.csv"""
        if gen_files:
            dst_path = f"{csv_gen.__name__}.csv"
            with open(dst_path, "w") as dst:
                csv_gen(dst)
        else:
            print(f"\n{csv_gen.__name__}")
            csv_gen(sys.stdout)

    CSV_GENS.append(_csv_gen_wrapped)
    return _csv_gen_wrapped


def wrap_standalone(txt):
    return (
        [
            r"\documentclass{standalone}",
            "",
            r"\usepackage{tikz}",
            r"\usepackage{pgfplots}",
            r"\usepgfplotslibrary{groupplots}",
            "",
            r"\definecolor{col1}{RGB}{53, 110, 175}",
            r"\definecolor{col2}{RGB}{204, 42, 42}",
            r"\definecolor{col3}{RGB}{255, 175, 35}",
            r"\definecolor{col4}{RGB}{79, 162, 46}",
            r"\definecolor{col5}{RGB}{97, 97, 97}",
            r"\definecolor{col6}{RGB}{103, 63, 153}",
            r"\definecolor{col7}{RGB}{0, 0, 0}",
            r"\definecolor{col8}{RGB}{123, 63, 0}",
            "",
            r"\begin{document}",
            "",
        ]
        + txt
        + [
            "",
            r"\end{document}",
        ]
    )


def wrap_pgfplots(txt):
    return (
        [
            r"\begin{tikzpicture}",
            r"\begin{groupplot}[",
            r"  width=.35\linewidth,",
            r"  group style={group size=4 by 1,group name=plots},",
            "]",
        ]
        + txt
        + [
            r"\end{groupplot}",
            r"\node at (plots c2r1.south)"
            + r"[inner sep=0pt, yshift=-12ex] {\ref{grouplegend}};",
            r"\end{tikzpicture}",
            "",
        ]
    )


def output_tex_file(lines, fname="dest", toFile=False, standalone=False, gen_pdf=False):
    lines = wrap_pgfplots(lines)
    if standalone:
        lines = wrap_standalone(lines)
    txt = "\n".join(lines)
    if toFile:
        with open(f"{fname}.tex", "w") as dst:
            dst.write(txt)
    else:
        sys.stdout.writelines(txt)

    if standalone and toFile and gen_pdf:
        subprocess.check_call(["tectonic", f"{fname}.tex"])


def load_data():
    data = []
    for fname in ["results_1D.json", "results_2D.json", "results_3D.json"]:
        with open(fname, "r") as src:
            data.append(json.load(src))
    return data


def compute_n_simplices(dim):
    simplices = [
        {"v": 1048576, "e": 1048575},  # 1D
        {"v": 16777216, "e": 50315265, "t": 33538050},  # 2D
        {"v": 7077888, "e": 42136128, "t": 69897596, "T": 34839355},  # 3D
    ]

    # number of simplices per dimension
    return functools.reduce(lambda a, b: a * b, simplices[dim].values())


def sort_datasets_by_n_pairs(data):
    n_pairs = {}

    # sum of number of DiscreteMorseSandwich pairs
    for ds, res in data.items():
        dsname = "_".join(ds.split("_")[:-3])
        for backend, perfs in res.items():
            if "DiscreteMorseSandwich" not in backend:
                continue
            n_pairs[dsname] = perfs["seq"].get("#Total pairs", 0)

    return dict(sorted(n_pairs.items(), key=lambda item: item[1]))


def transpose_data(data, dim, mode="seq"):
    # exec times per dataset per backend
    backend_ds_res = {}

    n_simplices = compute_n_simplices(dim)

    for ds, res in data.items():
        dsname = "_".join(ds.split("_")[:-3])
        for backend, perfs in res.items():
            if "Vertices" in backend:
                # print(dsname, n_pairs[dsname])
                continue
            if dim + 1 == 3 and "FTM" in backend:
                # no saddle-saddle pairs in FTM
                continue
            if mode == "seq" and backend in ["PHAT", "JavaPlex", "Gudhi"]:
                # parallel-only backends
                continue
            if mode == "para" and backend in [
                "Eirene.jl",
                "Perseus",
                "Diamorse",
                "Dionysus",
                "CubicalRipser",
            ]:
                # sequential-only backends
                continue

            if mode in perfs:
                val = perfs[mode]["pers"]
            elif "timeout" in perfs:
                val = perfs["timeout"]
            else:
                continue
            backend_ds_res.setdefault(backend, {}).update({dsname: n_simplices / val})

    return backend_ds_res


def generate_plot(data, backends, dim, mode="seq"):
    plot = [
        r"\nextgroupplot[legend to name=grouplegend, legend columns=7, title="
        + str(dim + 1)
        + "D datasets, ymode=log]"
    ]
    n_pairs_sorted = sort_datasets_by_n_pairs(data)
    backend_ds_res = transpose_data(data, dim, mode)

    for backend, legend in backends.items():
        try:
            coords = [r"\addplot[" + legend + "] coordinates {"]
            res = backend_ds_res[backend]
            for dsname, n_pairs in n_pairs_sorted.items():
                val = res[dsname]
                coords.append(f"({n_pairs}, {val})")
            coords.append("};")
            plot.append(" ".join(coords))
            plot.append(r"\addlegendentry{" + backend + "}")

        except KeyError:
            if backend == "TTK-FTM":
                plot.append(r"\addlegendimage{" + legend + "}")
                plot.append(r"\addlegendentry{" + backend + "}")

    return plot


def sort_backends(data, cpx="expl"):
    backends = {
        "DiscreteMorseSandwich": None,
        "PHAT": None,
        "Dipha": None,
        "Gudhi": None,
    }
    for d in data:
        for ds, res in d.items():
            if cpx not in ds:
                continue
            for backend in res.keys():
                if backend == "#Vertices":
                    continue
                backends[backend] = None
    legend = [
        "col1, mark=*",
        "col2, mark=square*",
        "col4, mark=x",
        "col3, mark=o",
        "col5, mark=triangle*",
        "col6, mark=diamond*",
        "col7, mark=star",
        "col8, mark=oplus*",
        "red, mark=pentagon*",
        "cyan, mark=asterisk",
        "teal, mark=pentagon",
        "lime, mark=star*",
        "orange, mark=triangle",
        "mark=o",
    ]
    return dict(zip(backends.keys(), legend))


def main():
    data = load_data()
    cpx = "expl"
    mode = "para"
    backends = sort_backends(data, cpx)

    res = []
    for i in range(3):
        res.extend(
            generate_plot(
                {k: v for k, v in data[i].items() if cpx in k}, backends, i, mode
            )
        )

    output_tex_file(res, f"plot_{cpx}_{mode}", True, True, True)


if __name__ == "__main__":
    main()

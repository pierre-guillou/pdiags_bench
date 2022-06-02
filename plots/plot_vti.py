import json
import subprocess
import sys


def wrap_standalone(txt):
    return (
        [
            r"""\documentclass{standalone}

\usepackage{lmodern}
\usepackage{hyperref}
\usepackage{tikz}
\usepackage{pgfplots}
\usepgfplotslibrary{groupplots}

\pgfplotsset{
  every axis/.append style={
    no markers,
    grid=major,
    grid style={dashed},
    legend style={font=\scriptsize},
    ylabel style={font=\scriptsize},
    xlabel style={font=\scriptsize},
  },
  every axis plot/.append style={line width=1.2pt, line join=round},
  every axis legend/.append style={legend columns=1},
  group/group size=3 by 1,
  every x tick label/.append style={alias=XTick,inner xsep=0pt},
  every x tick scale label/.style={at=(XTick.base east),anchor=base west}
}

\definecolor{col1}{RGB}{53, 110, 175}
\definecolor{col2}{RGB}{204, 42, 42}
\definecolor{col3}{RGB}{255, 175, 35}
\definecolor{col4}{RGB}{79, 162, 46}
\definecolor{col5}{RGB}{97, 97, 97}
\definecolor{col6}{RGB}{103, 63, 153}
\definecolor{col7}{RGB}{0, 0, 0}
\definecolor{col8}{RGB}{123, 63, 0}

\tikzset{
  curve1/.style={col1},
  curve2/.style={col2},
  curve3/.style={col4},
  curve4/.style={col3},
  curve5/.style={col6},
  curve6/.style={cyan},
  curve7/.style={col5, dashdotted},
  curve8/.style={col7, dashed},
  curve9/.style={col8, densely dotted},
  curve10/.style={teal},
  curve11/.style={lime},
  curve12/.style={orange},
}

\begin{document}
"""
        ]
        + txt
        + [
            r"""
\end{document}
"""
        ]
    )


def wrap_pgfplots(txt):
    return (
        [
            r"""\begin{tikzpicture}
\begin{groupplot}[
  group style={group name=plots,},
  xlabel=Output size  (\(\sum_{i = 0}^d |diagram_i(f)|\)),
]"""
        ]
        + txt
        + [
            r"""
\end{groupplot}
\node at (plots c2r1.east)[inner sep=0pt, xshift=15ex] {\pgfplotslegendfromname{grouplegend}};
\end{tikzpicture}
"""
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
    return [
        1048575,  # number of 1D edges
        16769025,  # number of 2D pixels
        6967871,  # number of 3D voxels
    ][dim]


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


def transpose_data(data, dim):
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

            if "para" in perfs:
                val = perfs["para"]["pers"]
            elif "seq" in perfs:
                val = perfs["seq"]["pers"]
            elif "timeout" in perfs:
                val = perfs["timeout"]
            else:
                continue
            backend_ds_res.setdefault(backend, {}).update({dsname: n_simplices / val})

    return backend_ds_res


def generate_plot(data, backends, dim):
    plot = [
        r"""\nextgroupplot[
  legend to name=grouplegend, ymode=log,
  ylabel=Computation speed (voxels/second),
]"""
    ]
    n_pairs_sorted = sort_datasets_by_n_pairs(data)
    backend_ds_res = transpose_data(data, dim)

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
        "col1",
        "col4",
        "col3",
        "col5, dashdotted",
        "col6, densely dashdotdotted",
        "col7, dashed",
        "col8, densely dotted",
        "red",
        "cyan",
        "teal",
        "lime",
        "orange",
        "black",
    ]
    return dict(zip(backends.keys(), legend))


def main():
    data = load_data()
    cpx = "impl"
    backends = sort_backends(data, cpx)

    res = []
    for i in range(1, 3):
        res.extend(
            generate_plot({k: v for k, v in data[i].items() if cpx in k}, backends, i)
        )

    output_tex_file(res, f"plot_{cpx}", True, True, True)


if __name__ == "__main__":
    main()

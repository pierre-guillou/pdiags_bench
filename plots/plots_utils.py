import subprocess


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

\newcommand{\diagram}{\mathcal{D}}

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


def wrap_pgfplots(txt, extra_group_opts="", legend_pos=""):
    txt = "\n".join(txt)
    return [
        rf"""\begin{{tikzpicture}}
\begin{{groupplot}}[
  group style={{group name=plots,}}, {extra_group_opts},
  xlabel=Output size  (\(\sum_{{i = 0}}^d |\diagram_i(f)|\)),]

{txt}

\end{{groupplot}}
{legend_pos}
\end{{tikzpicture}}
"""
    ]


def output_tex_file(
    lines,
    fname="dest",
    standalone=False,
    gen_pdf=False,
    extra_group_opts="",
    legend_pos="",
):
    lines = wrap_pgfplots(lines, extra_group_opts, legend_pos)
    if standalone:
        lines = wrap_standalone(lines)
    txt = "\n".join(lines)
    with open(f"{fname}.tex", "w") as dst:
        dst.write(txt)

    if standalone and gen_pdf:
        subprocess.check_call(["tectonic", f"{fname}.tex"])


def compute_n_simplices(dim):
    simplices = [
        {"v": 1048576, "e": 1048575},  # 1D
        {"v": 16777216, "e": 50315265, "t": 33538050},  # 2D
        {"v": 7077888, "e": 42136128, "t": 69897596, "T": 34839355},  # 3D
    ]

    # number of simplices per dimension
    return sum(simplices[dim].values())


def sort_datasets_by_n_pairs(data, mode="seq"):
    n_pairs = {}

    # sum of number of DiscreteMorseSandwich pairs
    for ds, res in data.items():
        dsname = "_".join(ds.split("_")[:-3])
        for backend, perfs in res.items():
            if "DiscreteMorseSandwich" not in backend:
                continue
            n_pairs[dsname] = perfs[mode].get("#Total pairs", 0)

    return dict(sorted(n_pairs.items(), key=lambda item: item[1]))

import json

import plots_utils


def load_data():
    data = []
    for fname in [
        "results_variants_1D.json",
        "results_variants_2D.json",
        "results_variants_3D.json",
    ]:
        with open(fname, "r") as src:
            data.append(json.load(src))
    return data


def transpose_data(data, dim, mode="seq"):
    # exec times per dataset per backend
    backend_ds_res = {}

    n_simplices = plots_utils.compute_n_simplices(dim)

    for ds, res in data.items():
        dsname = "_".join(ds.split("_")[:-3])
        for backend, perfs in res.items():
            if "Vertices" in backend:
                # print(dsname, n_pairs[dsname])
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
        r"\nextgroupplot[legend to name=grouplegend, ymode=log, "
        + ("ylabel=Computation speed (simplices/second),]" if dim == 0 else "]")
    ]

    n_pairs_sorted = plots_utils.sort_datasets_by_n_pairs(data, mode)
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

        except KeyError:
            plot.append(r"\addlegendimage{" + legend + "}")

        plot.append(r"\addlegendentry{" + backend.replace("_", r"\_") + "}")

    return plot


def sort_backends(data, cpx="expl"):
    backends = {
        "DiscreteMorseSandwich": None,
        "PairCells": None,
        "PairCriticalSimplices": None,
        "PairCriticalSimplices_BCaching": None,
        "PairCriticalSimplices_Sandwiching": None,
    }
    for d in data:
        for ds, res in d.items():
            if cpx not in ds:
                continue
            for backend in res.keys():
                if backend == "#Vertices":
                    continue
                backends[backend] = None
    return dict(
        zip(backends.keys(), ["curve" + str(i + 1) for i in range(len(backends))])
    )


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

        legend_pos = r"""\node at (plots c3r1.north east)[inner sep=0pt, xshift=-2ex, yshift=2ex]
  {\pgfplotslegendfromname{grouplegend}};"""

    plots_utils.output_tex_file(
        res,
        f"plot_variants_{cpx}_{mode}",
        False,
        False,
        r"width=.35\linewidth",
        legend_pos,
    )


if __name__ == "__main__":
    main()

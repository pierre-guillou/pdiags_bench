import json

import plots_utils


def load_data():
    data = []
    for fname in ["results_1D.json", "results_2D.json", "results_3D.json"]:
        with open(fname, "r") as src:
            data.append(json.load(src))
    return data


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

    n_simplices = plots_utils.compute_n_simplices(dim)

    for ds, res in data.items():
        dsname = "_".join(ds.split("_")[:-3])
        for backend, perfs in res.items():
            if "Vertices" in backend:
                # print(dsname, n_pairs[dsname])
                continue
            if dim + 1 == 3 and "FTM" in backend:
                # no saddle-saddle pairs in FTM
                continue
            if mode == "seq" and backend in ["JavaPlex", "Gudhi"]:
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
                val = n_simplices / perfs[mode]["mem"]
            else:
                val = 0
            backend_ds_res.setdefault(backend, {}).update({dsname: val})

    return backend_ds_res


def generate_plot(data, backends, dim, mode="seq"):
    plot = [
        "",
        "",
        r"\nextgroupplot[legend to name=grouplegend, ymode=log, "
        + ("ylabel=Memory Peak (simplices / MB),]" if dim == 0 else "]"),
    ]
    n_pairs_sorted = sort_datasets_by_n_pairs(data)
    backend_ds_res = transpose_data(data, dim, mode)

    for backend, legend in backends.items():
        if backend != "TTK-FTM" and backend not in backend_ds_res:
            continue
        try:
            coords = [r"\addplot[" + legend + "] coordinates {"]
            res = backend_ds_res[backend]
            vals = []
            for dsname, n_pairs in n_pairs_sorted.items():
                val = res[dsname]
                if val > 0:
                    vals.append(f"({n_pairs}, {val})")
            if len(vals) == 0:
                raise KeyError
            coords.extend(vals)
            coords.append("};")
            plot.append(" ".join(coords))
            plot.append(r"\addlegendentry{" + backend + "}")

        except KeyError:
            plot.append(r"\addlegendimage{" + legend + "}")
            plot.append(r"\addlegendentry{" + backend + "}")

    return plot


def sort_backends(data, cpx="expl"):
    backends = {
        "DiscreteMorseSandwich": None,
        "Dipha": None,
        "Gudhi": None,
        "TTK-FTM": None,
        "PersistenceCycles": None,
        "PHAT": None,
        "Eirene.jl": None,
        "JavaPlex": None,
        "Dionysus": None,
    }
    return dict(
        zip(backends.keys(), ["curve" + str(i + 1) for i in range(len(backends))])
    )


def main():
    data = load_data()
    cpx = "expl"
    backends = sort_backends(data, cpx)

    legend_pos = r"""\node at (plots c3r1.north east)[inner sep=0pt, xshift=-2ex, yshift=2ex]
{\pgfplotslegendfromname{grouplegend}};"""

    for mode in ["seq", "para"]:
        res = []
        for i in range(3):
            res.extend(
                generate_plot(
                    {k: v for k, v in data[i].items() if cpx in k}, backends, i, mode
                )
            )

        plots_utils.output_tex_file(
            res, f"plot_mem_{mode}", False, False, r"width=.35\linewidth", legend_pos
        )


if __name__ == "__main__":
    main()

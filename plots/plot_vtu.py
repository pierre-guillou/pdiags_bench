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
                val = perfs[mode]["pers"]
            elif "timeout" in perfs:
                val = perfs["timeout"]
            else:
                continue
            backend_ds_res.setdefault(backend, {}).update({dsname: val})

    return backend_ds_res


def generate_plot(data, backends, dim, mode="seq"):
    plot = [
        r"\nextgroupplot[legend to name=grouplegend, ymode=log, "
        + ("ylabel=Computation speed (simplices/second),]" if dim == 0 else "]")
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
            if backend == "DiscreteMorseSandwich":
                backend = "DMS"
            if backend == "PHAT_spectral_sequence":
                backend = r"PHAT (spectral\_sequence)"
            if backend == "PHAT_chunk":
                backend = "PHAT (chunk)"
            plot.append(r"\addlegendentry{" + backend + "}")

        except KeyError:
            if backend == "TTK-FTM":
                plot.append(r"\addlegendimage{" + legend + "}")
                plot.append(r"\addlegendentry{" + backend + "}")

    return plot


def sort_backends():
    backends = {
        "DiscreteMorseSandwich": "curve1",
        "Dipha": "curve2",
        "Gudhi": "curve6",
        "TTK-FTM": "curve5",
        "PersistenceCycles": "curve4",
        "PHAT_spectral_sequence": "curve3",
        "PHAT_chunk": "curve10",
        "Eirene.jl": "curve7",
        "JavaPlex": "curve8",
        "Dionysus": "curve9",
    }
    return backends


def main():
    data = load_data()
    cpx = "expl"
    backends = sort_backends()

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

        plots_utils.output_tex_file(res, f"plot_{cpx}_{mode}", False, False, legend_pos)


if __name__ == "__main__":
    main()

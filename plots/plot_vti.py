import json

import plots_utils


def load_data():
    data = []
    for fname in ["results_1D.json", "results_2D.json", "results_3D.json"]:
        with open(fname, "r") as src:
            data.append(json.load(src))
    return data


def compute_n_voxels(dim):
    return [
        1048575,  # number of 1D edges
        16769025,  # number of 2D pixels
        6967871,  # number of 3D voxels
    ][dim]


def transpose_data(data, dim):
    # exec times per dataset per backend
    backend_ds_res = {}

    n_simplices = compute_n_voxels(dim)

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


def generate_dat(data, dim, pref_mode="para"):

    n_pairs_sorted = plots_utils.sort_datasets_by_n_pairs(data)
    unpref_mode = "seq" if pref_mode == "para" else "para"
    n_simplices = compute_n_voxels(dim)

    backends = list(
        filter(
            lambda x: "#Vertices" not in x,
            data[next(filter(lambda x: "impl" in x, data))].keys(),
        )
    )

    header = ["nPairs"] + backends
    table = ["\t".join(header)]

    for ds, npairs in n_pairs_sorted.items():
        res = data[ds]
        line = []
        line.append(npairs)
        if "expl" in ds:
            continue
        for bk in backends:
            perfs = res[bk]
            if "error" in perfs:
                val = 0.0
            elif pref_mode in perfs:
                val = perfs[pref_mode]["pers"]
            elif unpref_mode in perfs:
                val = perfs[unpref_mode]["pers"]
            elif "timeout" in perfs:
                val = perfs["timeout"]
            line.append(n_simplices / val if val > 0.0 else 0.0)

        table.append("\t".join((str(a) for a in line)))

    with open(f"plot_vti_{pref_mode}_{dim + 1}D.dat", "w") as dst:
        dst.write("\n".join(table))


def generate_plot(data, backends, dim):
    plot = [
        r"\nextgroupplot[legend to name=grouplegend, ymode=log, "
        + ("ylabel=Computation speed (voxels/second),]" if dim == 1 else "]")
    ]
    n_pairs_sorted = plots_utils.sort_datasets_by_n_pairs(data)
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
        "TTK-FTM": None,
        "PersistenceCycles": None,
        "Oineus": None,
        "CubicalRipser": None,
        "Diamorse": None,
        "Perseus": None,
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
    cpx = "impl"
    backends = sort_backends(data, cpx)

    legend_pos = r"""\node at (plots c2r1.east)[inner sep=0pt, xshift=8ex]
{\pgfplotslegendfromname{grouplegend}};"""


    for mode in ["seq", "para"]:
        res = []
        for i in range(1, 3):
            res.extend(
                generate_plot({k: v for k, v in data[i].items() if cpx in k}, backends, i)
            )

        plots_utils.output_tex_file(res, f"plot_{cpx}_{mode}", False, False, "", legend_pos)


if __name__ == "__main__":
    main()

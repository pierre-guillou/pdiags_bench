import json


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


def transpose_data(data):
    # exec times per dataset per backend
    backend_ds_res = {}

    for ds, res in data.items():
        if "impl" in ds:
            continue
        dsname = "_".join(ds.split("_")[:-3])
        for backend, perfs in res.items():
            if "Vertices" in backend:
                continue

            if "para" in perfs:
                val = perfs["para"]["pers"]
            else:
                val = perfs["timeout"]
            backend_ds_res.setdefault(backend, {}).update({dsname: val})

    return backend_ds_res


def main():
    data = load_data()

    res = [{}, {}, {}]

    for dim in range(3):
        backend_ds_res = transpose_data(data[dim])
        for bk, perf in backend_ds_res.items():
            mean = 0.0
            for val in perf.values():
                mean += val
            if bk == "DiscreteMorseSandwich":
                print(perf)
            mean /= len(perf)
            res[dim][bk] = mean

    for i, dim_res in enumerate(res):
        print(f"{i + 1}D:")
        for k, v in sorted(dim_res.items()):
            print(f"  {k}: {v} s")

    mean_pc_speedup = [{}, {}, {}]
    for dim in range(3):
        for ds, bk in data[dim].items():
            if "impl" in ds:
                continue
            dms_val = bk["DiscreteMorseSandwich"]["para"]["pers"]
            if "para" in bk["PairCells"]:
                pc_val = bk["PairCells"]["para"]["pers"]
                mean_pc_speedup[dim][ds] = pc_val / dms_val

    for i, dim_res in enumerate(mean_pc_speedup):
        print(f"{i + 1}D: ({len(dim_res)} datasets without PairCells timeout)")
        mean = sum(dim_res.values()) / len(dim_res.values())
        print(f"  Mean DiscreteMorseSandwich speedup over PairCells: {mean}")


if __name__ == "__main__":
    main()

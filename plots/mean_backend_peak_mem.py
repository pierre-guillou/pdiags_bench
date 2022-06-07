import json


def load_data():
    data = []
    for fname in ["results_1D.json", "results_2D.json", "results_3D.json"]:
        with open(fname, "r") as src:
            data.append(json.load(src))
    return data


def transpose_data(data, mode="seq"):
    # exec times per dataset per backend
    backend_ds_res = {}

    for ds, res in data.items():
        if "impl" in ds:
            continue
        dsname = "_".join(ds.split("_")[:-3])
        for backend, perfs in res.items():
            if "Vertices" in backend:
                continue

            if mode in perfs:
                val = perfs[mode]["mem"]
            else:
                continue
            backend_ds_res.setdefault(backend, {}).update({dsname: val})

    return backend_ds_res


def main():
    data = load_data()

    res = {
        "seq": [{}, {}, {}],
        "para": [{}, {}, {}],
    }

    for dim in range(3):
        for mode in ["seq", "para"]:
            backend_ds_res = transpose_data(data[dim], mode)
            for bk, perf in backend_ds_res.items():
                mean = 0.0
                for val in perf.values():
                    mean += val
                mean /= len(perf)
                res[mode][dim][bk] = mean

    for i in range(3):
        print(f"{i + 1}D mean memory peak (MB):")
        for mode in ["seq", "para"]:
            print(f"  {mode}")
            for k, v in res[mode][i].items():
                print(f"    {k:<30}{v:>10.1f}")


if __name__ == "__main__":
    main()

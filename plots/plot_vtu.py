import functools
import json
import math
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


fname = "results_2D.json"
with open(fname, "r") as src:
    data = json.load(src)

simplices = {
    "1D": {"v": 1048576, "e": 1048575},
    "2D": {"v": 16777216, "e": 50315265, "t": 33538050},
    "3D": {"v": 7077888, "e": 42136128, "t": 69897596, "T": 34839355},
}

# number of simplices per dimension
n_simplices = [
    functools.reduce(lambda a, b: a * b, d.values()) for d in simplices.values()
]

# only explicit data-sets
data_vtu = {k: v for k, v in data.items() if "expl" in k}

n_pairs = {}

# sum of number of DiscreteMorseSandwich pairs
for ds, res in data_vtu.items():
    dsname = "_".join(ds.split("_")[:-3])
    for backend, perfs in res.items():
        if "DiscreteMorseSandwich" not in backend:
            continue
        n_pairs[dsname] = perfs["seq"].get("#Total pairs", 0)

res = {}

# exec times
for ds, res in data_vtu.items():
    dsname = "_".join(ds.split("_")[:-3])
    for backend, perfs in res.items():
        if "Vertices" in backend:
            print(dsname, n_pairs[dsname])
            continue
        if "seq" in perfs:
            val = perfs["seq"]["pers"]
        elif "timeout" in perfs:
            val = perfs["timeout"]
        print(dsname, backend, math.log(n_simplices[1] / val))

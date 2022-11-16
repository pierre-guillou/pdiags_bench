import json
import statistics

import plots_utils


def process_data(datafile, dim):
    with open(datafile, "r") as src:
        data = json.load(src)

    minima = []
    maxima = []
    s1 = []
    s2 = []
    total = []

    n_simplices = plots_utils.compute_n_simplices(dim)

    for ds, el in data.items():
        if "impl" in ds:
            continue
        nmin = int(el["DiscreteMorseSandwich"]["seq"]["#Min-saddle"])
        minima.append(nmin / n_simplices)
        if "1D" in datafile:
            maxima.append(nmin / n_simplices)
        else:
            nmax = int(el["DiscreteMorseSandwich"]["seq"]["#Saddle-max"])
            maxima.append(nmax / n_simplices)
        if "3D" in datafile:
            d2 = int(el["DiscreteMorseSandwich"]["seq"].get("#Saddle-saddle", 0))
            s1.append((nmin + d2) / n_simplices)
            s2.append((nmax + d2) / n_simplices)
        elif "2D" in datafile:
            s1.append((nmin + nmax) / n_simplices)
            s2.append(0)
        else:
            s1.append(0)
            s2.append(0)
        total.append(minima[-1] + maxima[-1] + s1[-1] + s2[-1])

    data = {"min": minima, "max": maxima, "s1": s1, "s2": s2, "total": total}

    res = {}

    for label, el in data.items():
        res[label] = {
            "min": min(el),
            "max": max(el),
            "mean": statistics.mean(el),
            "stdev": statistics.stdev(el),
        }

    return res


def print_table(stats):
    print(r"\begin{tabular}[ht]{ll|rrr|}")
    print(r"\hline")
    print(r"& & min & max & avg \\")
    print(r"\hline")

    keys = [
        ["min", "max", "total"],
        ["min", "s1", "max", "total"],
        ["min", "s1", "s2", "max", "total"],
    ]

    for dim, stat in enumerate(stats):
        for key in keys[dim]:
            row = []
            if key == "min":
                row.append(rf"\multirow{{{dim + 3}}}{{*}}{{{dim + 1}D}} & {key}")
            else:
                row.append(f"& {key}")
            row.extend(
                [
                    f"{stat[key]['min']:%}",
                    f"{stat[key]['max']:%}",
                    f"{stat[key]['mean']:%}",
                ]
            )
            row = " & ".join(str(v) for v in row)
            row = row.replace("%", r"\%")
            print(rf"{row} \\")
        print(r"\hline")
    print(r"\end{tabular}")


def main():
    stats = []

    for d, datafile in enumerate(
        ["results_1D.json", "results_2D.json", "results_3D.json"]
    ):
        stats.append(process_data(datafile, d))

    print_table(stats)


if __name__ == "__main__":
    main()

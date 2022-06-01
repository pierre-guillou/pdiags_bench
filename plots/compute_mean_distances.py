import pathlib
import sys

sys.path.append("..")

import compare_diags


def main():
    backend_ref = "TTK-Sandwich"
    cpx = "expl"

    p = pathlib.Path("../diagrams")
    backends = set()
    for diag_ref in sorted(p.glob(f"*{cpx}_{backend_ref}*")):
        ds_root = "_".join(diag_ref.stem.split("_")[:-1])
        for diag in sorted(p.glob(f"{ds_root}*")):
            if backend_ref in diag.name:
                continue
            backends.add(diag.stem.split("_")[-1])

    backends = sorted(list(backends))
    print(backends)
    dists = {}

    for bk in backends:
        if bk in ["PersistenceCycles"]:
            # not working yet
            continue
        for diag_ref in sorted(p.glob(f"*{cpx}_{backend_ref}*")):
            ds_root = "_".join(diag_ref.stem.split("_")[:-1])
            ds_bk = f"{ds_root}_{bk}"
            for diag in sorted(p.glob(f"*{ds_bk}*")):
                res = compare_diags.main(str(diag_ref), str(diag), False)
                dists.setdefault(bk, []).append(sum(res.values()))

    for bk, res_l in dists.items():
        print(bk, res_l)
        dists[bk] = sum(res_l) / len(res_l) if len(res_l) != 0 else 0

    print(dists)


if __name__ == "__main__":
    main()

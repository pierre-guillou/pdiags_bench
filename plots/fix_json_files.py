import argparse
import json


def main(json0, json1, dry_run=True):
    with open(json0, "r") as src:
        data0 = json.load(src)
    with open(json1, "r") as src:
        data1 = json.load(src)

    for k in data1.keys():
        # datasets
        if not k in data0:
            print(f"adding {data1[k]}")
            data0[k] = data1[k]
        else:
            # backends
            for kk in data1[k].keys():
                if kk not in data0[k] or "error" in data0[k][kk]:
                    print(f"adding {k}: {{{kk}: {data1[k][kk]}}}")
                    data0[k][kk] = data1[k][kk]

    if not dry_run:
        with open(json0, "w") as dst:
            json.dump(data0, dst, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Modify first JSON file with missing values from the second one"
    )
    parser.add_argument("json0", help="Reference JSON file (to be modified)")
    parser.add_argument("json1", help="Source JSON file (contains the modifications)")
    parser.add_argument("-n", "--dry-run", help="Dry run", action="store_true")

    args = parser.parse_args()
    main(args.json0, args.json1, args.dry_run)

import argparse
import json


def main(json0, json1, dry_run=True):
    with open(json0, "r") as src:
        data0 = json.load(src)
    with open(json1, "r") as src:
        data1 = json.load(src)

    for k in data1.keys():
        # datasets
        if "impl" in k:
            continue
        # backends
        print(
            f'{data0[k]["Dipha"]["para"]["mem"]} <- {data1[k]["Dipha"]["para"]["mem"]}'
        )
        data0[k]["Dipha"]["para"]["mem"] = data1[k]["Dipha"]["para"]["mem"]

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

import argparse
import pathlib


def read_pairs(fname):
    pairs = list()
    with open(fname, "r") as src:
        lines = src.readlines()
        for line in lines:
            pairs.append([int(x) for x in line.split(" ")])
    return pairs


def write_pairs(pairs, output, dim):
    with open(output, "a") as dst:
        for pair in pairs:
            birth = pair[0]
            death = pair[1]
            if death == -1:
                death = "inf"
            dst.write(f"{dim} {birth} {death}\n")


def main(pers_input, gudhi_output):
    p = pathlib.Path(gudhi_output)
    if p.exists():
        p.unlink()

    for i in range(4):
        p = pathlib.Path(pers_input + "_" + str(i) + ".txt")
        if p.exists():
            pairs = read_pairs(p)
            write_pairs(pairs, gudhi_output, i)
            p.unlink()
        else:
            print(f"{p} not found")

    p = pathlib.Path(pers_input + "_betti.txt")
    if p.exists():
        p.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a Perseus diagram into a Gudhi diagram"
    )

    parser.add_argument(
        "input_diagram", type=str, help="Persistence Diagram in Perseus format"
    )
    parser.add_argument(
        "output_diagram",
        type=str,
        help="Output Gudhi format file name",
        default="out.gudhi",
    )
    args = parser.parse_args()

    main(args.input_diagram.split("_")[0], args.output_diagram)

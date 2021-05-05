import argparse


def read_pairs(fname):
    pairs = list()
    with open(fname, "r") as src:
        lines = src.readlines()
        for line in lines:
            if line.startswith("#"):
                continue
            pairs.append(line.split()[:3])
    return pairs


def write_pairs(pairs, output):
    with open(output, "w") as dst:
        for birth, death, dim in pairs:
            dst.write(f"{dim} {birth} {death}\n")


def main(diamorse_input, gudhi_output):
    pairs = read_pairs(diamorse_input)
    write_pairs(pairs, gudhi_output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a Diamorse diagram into a Gudhi diagram"
    )

    parser.add_argument("input_diagram", help="Persistence Diagram in Diamorse format")
    parser.add_argument(
        "output_diagram",
        help="Output Gudhi format file name",
        default="out.gudhi",
    )
    args = parser.parse_args()

    main(args.input_diagram, args.output_diagram)

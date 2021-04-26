def main(input_diag, output):
    pairs = list()
    with open(input_diag) as src:
        lines = src.readlines()
        for line in lines:
            if not line.startswith("#"):
                pairs.append(line.split()[0:3])

    with open(output, "w") as dst:
        for birth, death, dim in pairs:
            dst.write(f"{dim} {birth} {death}\n")


if __name__ == "__main__":
    main("../diamorse/pairs.txt", "out.gudhi")

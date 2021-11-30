import glob

import compare_diags


def main():
    for ds in sorted(glob.glob("diagrams/*_expl_Dipha.dipha")):
        ttk_diag = str(ds).replace("Dipha.dipha", "TTK-Sandwich.vtu")
        compare_diags.main(ds, ttk_diag, False)


if __name__ == "__main__":
    main()

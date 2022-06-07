import re
import sys


def escape_ansi_chars(txt):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", txt)


def ttk_compute_time(ttk_output):
    ttk_output = escape_ansi_chars(ttk_output)
    time_re = r"\[PersistenceDiagram\] Complete.*\[(\d+\.\d+|\d+)s"
    cpt_time = float(re.search(time_re, ttk_output, re.MULTILINE).group(1))
    overhead = ttk_overhead_time(ttk_output)
    return cpt_time - overhead


def ttk_overhead_time(ttk_output):
    time_re = r"\[DiscreteGradient\] Memory allocations.*\[(\d+\.\d+|\d+)s"
    try:
        return float(re.search(time_re, ttk_output, re.MULTILINE).group(1))
    except AttributeError:
        return 0.0


def ttk_prec_time(ttk_output):
    ttk_output = escape_ansi_chars(ttk_output)
    prec_re = r"\[PersistenceDiagram\] Precondition triangulation.*\[(\d+\.\d+|\d+)s"
    prec_time = float(re.search(prec_re, ttk_output, re.MULTILINE).group(1))
    return prec_time


def dipha_compute_time(dipha_output):
    run_pat = r"^Overall running time.*\n(\d+.\d+|\d+)$"
    run_time = re.search(run_pat, dipha_output, re.MULTILINE).group(1)
    run_time = float(run_time)
    read_pat = r"^ *(\d+.\d+|\d+)s.*complex.load_binary.*$"
    read_time = re.search(read_pat, dipha_output, re.MULTILINE).group(1)
    read_time = float(read_time)
    write_pat = r"^ *(\d+.\d+|\d+)s.*save_persistence_diagram.*$"
    write_time = re.search(write_pat, dipha_output, re.MULTILINE).group(1)
    write_time = float(write_time)
    prec = round(read_time + write_time, 3)
    pers = round(run_time - prec, 3)
    return prec, pers


def phat_compute_time(output):
    pers_pat = r"Computing persistence pairs took (\d+.\d+|\d+)s"
    pers = re.search(pers_pat, output, re.MULTILINE).group(1)
    pers = round(float(pers), 3)
    return pers


def main():
    lines = []
    with open(sys.argv[1]) as src:
        lines = src.readlines()

    pat = r"Processing .*\/(.*)_192x192x192_order_expl.* with (.*) with (\d*) .*"
    delimiters = []
    sections = []
    for i, line in enumerate(lines):
        if "Processing" in line:
            # print(i, line.strip())
            delimiters.append(i)
            sections.append(re.search(pat, line).groups())

    delimiters.append(len(lines))
    res = {sec[0]: {"TTK": {}, "Dipha": {}, "PHAT": {}} for sec in sections}
    for i, sec in enumerate(sections):
        seclog = "".join(lines[slice(delimiters[i], delimiters[i + 1])])
        try:
            if sec[1] == "TTK":
                res[sec[0]][sec[1]][int(sec[2])] = ttk_compute_time(seclog)
            elif sec[1] == "Dipha":
                res[sec[0]][sec[1]][int(sec[2])] = dipha_compute_time(seclog)[1]
            elif sec[1] == "PHAT":
                res[sec[0]][sec[1]][int(sec[2])] = phat_compute_time(seclog)
        except AttributeError:
            break

    for k, v in sorted(res.items()):
        print(k)
        for kk, vv in v.items():
            print("  ({}, {})".format(kk, sorted(vv.items())))


if __name__ == "__main__":
    main()

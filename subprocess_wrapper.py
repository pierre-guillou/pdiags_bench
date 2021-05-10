import argparse
import resource
import subprocess
import sys


def main(cmd):
    subprocess.run(cmd, check=True)
    res = resource.getrusage(resource.RUSAGE_CHILDREN)
    print(f"Elapsed Time (s): {res.ru_utime}", file=sys.stderr)
    print(f"Peak Memory (kB): {res.ru_maxrss}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GNU Time replacement")
    parser.add_argument("cmd", nargs="+")
    args = parser.parse_args()
    main(args.cmd)

import argparse
import resource
import subprocess
import sys
import time


def main(cmd):
    beg = time.time()
    subprocess.run(cmd, check=True)
    end = time.time()
    res = resource.getrusage(resource.RUSAGE_CHILDREN)
    print(f"Elapsed Time (s): {end - beg}", file=sys.stderr)
    print(f"Peak Memory (kB): {res.ru_maxrss}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GNU Time replacement")
    parser.add_argument("cmd", nargs="+")
    args = parser.parse_args()
    main(args.cmd)

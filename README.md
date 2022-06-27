Benchmark suite for Persistence Diagrams Libraries
==================================================


* [TTK](https://topology-tool-kit.github.io)
* [Dipha](https://github.com/DIPHA/dipha)
* [Gudhi](https://gudhi.inria.fr/)
* [Perseus](https://people.maths.ox.ac.uk/nanda/perseus/index.html)
* [CubicalRipser](https://github.com/CubicalRipser/CubicalRipser_3dim)
* [Diamorse](https://github.com/AppliedMathematicsANU/diamorse)
* [Oineus](https://github.com/grey-narn/oineus)
* [Dionysus2](https://mrzv.org/software/dionysus2)
* [Eirene.jl](https://github.com/Eetion/Eirene.jl)
* [Ripser](https://github.com/Ripser/ripser)
* [PersistentCycles](https://github.com/IuricichF/PersistenceCycles)
* [PHAT](https://bitbucket.org/phat-code/phat)

This project uses [Poetry](https://python-poetry.org/) to manage the
Python dependencies.

## 0. Prerequisites

To run the benchmark, please use a computer/virtual machine with
* Ubuntu 20.04 (preferred)
* at least 64GB of RAM (it might even swap)
* at least 1500GB of free disk space for storing the converted input datasets
* at least 150h of computing time

If those requirements are too heavy, you can
* reduce the number of downloaded datasets (default max size: 1024MB)
* reduce the resampling size (default: 192 for a grid of 192^3 vertices)

## 1. Installing the dependencies

```sh
# install build dependencies
$ sudo apt install g++ cmake python-numpy pipx python3-dev python3-venv libeigen3-dev \
    julia default-jdk libtbb-dev libboost-dev python2-dev libopenmpi-dev libgl1-mesa-dev
# install poetry with pipx
$ /usr/bin/python3 -m pipx install poetry
# install run-time dependencies
$ ~/.local/bin/poetry install
```

## 2. Building the missing software libraries

```sh
$ ~/.local/bin/poetry run python build_software.py
```

## 3. Fetching the OpenSciVis datasets (raw files) & converting them to supported input formats

```sh
$ ~/.local/bin/poetry run python main.py prepare_datasets -d
```

Use the `--max_dataset_size xxx` flag to change the number of downloaded
datasets (default 1024MB). Use the `--max_resample_size yyy` flag to
modify the resampled size (default 192 for a 192^3 grid)

## 4. Launch the Persistence Diagram computation

```sh
$ ~/.local/bin/poetry run python main.py compute_diagrams
```

Use the `--sequential` key to request a sequential execution (parallel
for TTK, Dipha and Oineus by default).

A whole run can up to 150h of computation time. To reduce it, the
flags `-1`, `-2` or `-3` can be used to specify the dimension of the
input dataset.

## 5. Observe the results

Once the previous step has been completed, timings results are stored
using the JSON format in a timestamped file. This text file can be
read using any text editor:

```sh
$ less results-*timestamp*.json
```

### 6. Compute distances between diagrams

The script [./compute_mean_distances.py](compute_mean_distances.py) is
used to compare the pairs of every computed diagrams to a reference
(here the DiscreteMorseSandwich backend). The distance computation uses
a quick approach that detects and filters out identical pairs between
two diagrams. The Wasserstein distance is then computed on the
non-identical remaining pairs.

```sh
$ ~/.local/bin/poetry run python compute_mean_distances.py
```

The scripts returns the mean distance aggregated per backend.

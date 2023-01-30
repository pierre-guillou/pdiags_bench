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

## 0. Prerequisites

To run the benchmark, please use a computer/virtual machine with
* Ubuntu 20.04 (preferred)
* at least 64GB of RAM (it might even swap)
* at least 1500GB of free disk space for storing the converted input datasets
* at least 150h of computing time

If those requirements are too heavy, you can
* reduce the number of downloaded datasets (default max size: 1024MB)
* reduce the resampling size (default: 192 for a grid of 192^3 vertices)

### Replicability stamp
For the replicability stamp, we provide below, for each section, a second set of commands which will restrict the benchmark to only a subset of the tests. This will therefore significantly reduce both storage space and computation time. For this version of the benchmark, please use a computer/virtual machine with
* Ubuntu 20.04 (preferred)
* at least 64GB of RAM (it might even swap)
* at least 175GB of free disk space for storing the converted input datasets
* at least 7h of computing time

## 1. Installing the dependencies

```sh
# 1. install the build dependencies
$ sudo apt update
$ sudo apt install g++ git python-numpy python3-dev python3-pip libeigen3-dev \
    julia default-jdk libtbb-dev libboost-dev python2-dev libopenmpi-dev \
    libgl1-mesa-dev texlive-latex-extra latexmk
# 2. clone the repository
$ git clone https://github.com/pierre-guillou/pdiags_bench
$ cd pdiags_bench
# 3. expand PATH
$ export PATH=$PATH:$HOME/.local/bin
# 4. install cmake first
$ /usr/bin/python3 -m pip install cmake
# 5. install run-time dependencies
$ /usr/bin/python3 -m pip install -r requirements.txt
```

## 2. Building the missing software libraries

```sh
$ python3 build_software.py
```

### Replicability stamp
For the replicability stamp, enter this command (to only build a restricted set of implementations)

```sh
$ python3 build_software.py -s
```
This step should take approximately one hour on a commodity computer.


## 3. Fetching the OpenSciVis datasets (raw files) & converting them to supported input formats

```sh
$ python3 main.py prepare_datasets -d
```

Use the `--max_dataset_size xxx` flag to change the number of downloaded
datasets (default 1024MB). Use the `--max_resample_size yyy` flag to
modify the resampled size (default 192 for a 192^3 grid)

### Replicability stamp
For the replicability stamp, enter this command (to only download a restricted set of datasets)

```sh
$ python3 main.py prepare_datasets -d --max_dataset_size 1
```
This step should take approximately forty minutes on a commodity computer.

## 4. Launch the Persistence Diagram computation

### 1D datasets
```sh
$ python3 main.py compute_diagrams -1
```

### 2D datasets
```sh
$ python3 main.py compute_diagrams -2
```

### 3D datasets
```sh
$ python3 main.py compute_diagrams -3
```

Use the `--sequential` key to request a sequential execution (parallel
for TTK, Dipha and Oineus by default).

A default timeout of 1800s (30min) is set at every diagram computation
to avoid spending too much time. This timeout can be reduced using the
`-t` flag. For instance, a timeout of 10 minutes is set with `-t 600`.

### Replicability stamp
For the replicability stamp, enter this command (to only process 3D data)
```sh
$ python3 main.py compute_diagrams -3 -t 600
```
This step should take approximately five hours on a commodity computer.

## 5. Observe the results

Once the previous steps have been completed, timings results are stored
using the JSON format in timestamped files (one per run). This text file can be
read using any text editor:

```sh
$ less results-*timestamp*.json
```

Python scripts inside the `plots` subfolder can generate LaTeX and/or
corresponding PDFs files.

Specifically, first copy each generated JSON file to the appropriate target
```sh
$ cp results-*timestamp_for_the_1D_dataset_run*.json plots/results_1D.json
$ cp results-*timestamp_for_the_2D_dataset_run*.json plots/results_2D.json
$ cp results-*timestamp_for_the_3D_dataset_run*.json plots/results_3D.json
```

Next, the Figures 18 and 19 of the IEEE TVCG paper "Discrete Morse
Sandwich: Fast Computation of Persistence Diagrams for Scalar Data –
An Algorithm and A Benchmark" can be reproduced with the following command

```sh
cd plots
python3 plot_vtu.py
```

This will generate two LaTeX files and the corresponding PDFs files
built with `latexmk`. These files are named `plot_expl_seq.pdf` (Fig. 18 of the
paper) for
the sequential results and `plots_expl_para.pdf` (Fig. 19 of the paper) for the parallel
results (same names for the LaTeX source files).

Input data (result timings) is stored inside the `.json` files in the
same subfolder. Overwrite these and re-run the script to update the
PDFs.

### Replicability stamp
For the replicability stamp, enter these commands

```sh
cp results-*timestamp_for_the_3D_dataset_run*.json plots/results_3D.json
cd plots
python3 plot_vtu.py
```
The rightmost sub-figure of the file `plots_expl_para.pdf` (i.e. 3D datasets) replicates the rightmost sub-figure of the Figure 19 of the paper (with fewer datasets, i.e. fewer data points).

## 6. Compute distances between diagrams

The script [./compute_mean_distances.py](compute_mean_distances.py) is
used to compare the pairs of every computed diagrams to a reference
(here the DiscreteMorseSandwich backend). The distance computation uses
a quick approach that detects and filters out identical pairs between
two diagrams. The Wasserstein distance is then computed on the
non-identical remaining pairs.

```sh
$ python3 compute_mean_distances.py
```

The scripts returns the mean distance aggregated per backend.

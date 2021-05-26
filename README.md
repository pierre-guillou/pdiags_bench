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

This project uses [Poetry](https://python-poetry.org/) to manage the
Python dependencies.

0. Prerequisites

To run the benchmark, please use a computer/virtual machine with
* Ubuntu 20.04 (preferred)
* at least 64GB of RAM (it might even swap)
* at least 700GB of free disk space for storing the converted input datasets
* at least 100h of computing time

If those requirements are too heavy, you can
* reduce the number of downloaded datasets (default max size: 1024MB)
* reduce the resampling size (default: 192 for a grid of 192^3 vertices)

1. Installing the dependencies

```
sudo apt install python-numpy pipx julia default-jdk
/usr/bin/python3 -m pipx install poetry
poetry install
```
TODO: ParaView + TTK (via deb packages?)


2. Building the missing software libraries

```
poetry run python build_software.py
```

3. Fetching the OpenSciVis datasets (raw files) & converting them to
   supported input formats

```
poetry run python main.py prepare_datasets -d
```

Use the `--max_dataset_size xxx` flag to change the number of downloaded
datasets (default 1024MB). Use the `--max_resample_size yyy` flag to
modify the resampled size (default 192 for a 192^3 grid)

4. Launch the Persistence Diagram computation

```
poetry run python main.py compute_diagrams
```

Use the `--sequential` key to request a sequential execution (parallel
for TTK, Dipha and Oineus by default).

5. Observe the results, generate a LaTeX table

```
python -m json.tool results
poetry run python res2tex results
```

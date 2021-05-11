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

1. Installing the dependencies

```
sudo apt install python-numpy pipx
pipx install poetry
poetry install
```

2. Building the missing software libraries

```
poetry run python build_software.py
```

3. Fetching the OpenSciVis datasets (raw files) & converting them to
   supported input formats

```
poetry run python main.py prepare_datasets -d
```

4. Launch the Persistence Diagram computation

```
poetry run python main.py compute_diagrams
```

5. Observe the results, generate a LaTeX table

```
python -m json.tool results
poetry run python res2tex results
```

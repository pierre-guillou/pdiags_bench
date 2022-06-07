## Environment

In an `env.sh` file:

```sh
# installation prefix
PREFIX=$HOME/install
# helps CMake find ParaView
export CMAKE_PREFIX_PATH=$PREFIX/lib64:$CMAKE_PREFIX_PATH
export LD_LIBRARY_PATH=$PREFIX/lib64:$LD_LIBRARY_PATH
export PYTHONPATH=$PREFIX/lib64/python3.9/site-packages
# for pvpython & TTK standalones
export PATH=$PREFIX/bin:$PATH
# ParaView needs it to find TTK
export PV_PLUGIN_PATH=$PREFIX/bin/plugins/TopologyToolKit
# make builds with 4 processes in parallel
export MAKEFLAGS="-j4"

# load modules at login
module load python/3.9 cmake/3.19 gcc/8.2
```

(no gcc/11.2 since GMP (<limits>) is incompatible with TTK)

Then

```sh
echo "source env.sh" >> .bashrc
```

## Boost

```sh
wget https://boostorg.jfrog.io/artifactory/main/release/1.77.0/source/boost_1_77_0.tar.gz

# should be 5347464af5b14ac54bb945dc68f1dd7c56f0dad7262816b956138fc53bcc0131
sha256sum boost_1_77_0.tar.gz

tar xzf boost_1_77_0.tar.gz
```
## ParaView

```sh
git clone --depth 10 https://github.com/topology-tool-kit/ttk-paraview
cd ttk-paraview
mkdir build
cd build
CC=gcc CXX=g++ cmake -DPARAVIEW_USE_QT=OFF -DCMAKE_INSTALL_PREFIX=$HOME/install ..
make install
```

## TTK


```sh
git clone --depth 10 https://github.com/topology-tool-kit/ttk
cd ttk
mkdir build
cd build
CC=gcc CXX=g++ \
  cmake \
  -DCMAKE_INSTALL_PREFIX=$HOME/install \
  -DBoost_INCLUDE_DIR=$HOME/boost_1_77_0 \
  -DTTK_ENABLE_CPU_OPTIMIZATION=OFF \
  -DTTK_ENABLE_KAMIKAZE=ON \
  ..
make install
```

## Test installation

```sh
python3.9 -c "import vtk, topologytoolkit"
python3.9 -c "from paraview import simple;simple.TTKPersistenceDiagram"
```

## DIPHA

```sh
module load cmake/3.19 gcc/8.2 openMPI/4.1.2-gcc82
mkdir build && cd build
CC=gcc CXX=g++ MPI_HOME=/opt/dev/libs/OpenMPI-4.1.2-gcc82 cmake ..
make
```

## PHAT

```sh
module load cmake/3.19 gcc/8.2
mkdir build && cd build
CC=gcc CXX=g++ cmake ..
make
```

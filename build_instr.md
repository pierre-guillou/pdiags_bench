# Common modules

```bash
$ module load python/3.9 cmake/3.22 openMPI/4.1.2-gcc82 gcc/8.2
```

# Dipha with MPI

* OpenMPI
  + module load openMPI
  + CC=mpicc CXX=mpicxx CXXFLAGS=-std=c++11 MPI_HOME=/opt/dev/libs/OpenMPI-4.0.3-intel ccmake ../../dipha
* MPT
  + module load mpt/2.18
  + CC=mpicc CXX=mpicxx MPI_HOME=/opt/hpe/hpc/mpt/mpt-2.18 ccmake ../../dipha
* Intel
  + module load intel/intel-compilers-18.2/18.2 intel/intel-mpi/2018.2
  + CC=icc CXX=icpc CXXFLAGS=-std=c++11 MPI_ROOT=/opt/dev/intel/2018_Update2/impi/2018.2.199 ccmake ../../dipha

```bash
$ CC=mpicc CXX=mpicxx CXXFLAGS=-std=c++11 MPI_HOME=/opt/dev/libs/OpenMPI-4.1.2-gcc82 \
  ccmake -DCMAKE_BUILD_TYPE=Release ..
```

# ParaView

* GCC and Python
```
$ CC=gcc CXX=g++ ccmake \
  -DPARAVIEW_USE_QT=OFF \
  -DCMAKE_INSTALL_PREFIX=$HOME/install_pv56 \
  -DCMAKE_BUILD_TYPE=Release \
  ..
```

# TTK with OpenMP (FTM + DiscreteMorseSandwich)

* GCC and SGI MPT
```bash
$ CC=gcc CXX=g++ ccmake \
  -DVTK_DIR=$HOME/install/lib/cmake/paraview-5.10 \
  -DBoost_INCLUDE_DIR=$HOME/boost_1_77_0 \
  -DTTK_ENABLE_CPU_OPTIMIZATIONS=OFF \
  -DTTK_ENABLE_KAMIKAZE=ON \
  -DCMAKE_INSTALL_PREFIX=$HOME/install \
  -DCMAKE_BUILD_TYPE=Release ..
```

# PHAT (no install)

```bash
$ CC=gcc CXX=g++ ccmake -DCMAKE_BUILD_TYPE=Release ..
```

# PersistenceCycles

1. ParaView

```bash
$ CC=gcc CXX=g++ ccmake \
  -DPARAVIEW_BUILD_QT_GUI=OFF \
  -DVTK_Group_ParaViewRendering=OFF \
  -DCMAKE_INSTALL_PREFIX=$HOME/install_pv56 \
  -DCMAKE_BUILD_TYPE=Release \
  ..
```

2. patches

```bash
$ git apply $HOME/pdiags_bench/patches/PersistenceCycles*
```

3. PersistenceCycles

```bash
$ CC=gcc CXX=g++ ccmake \
  -DVTK_DIR=$HOME/install_pv56/lib/cmake/paraview-5.6 \
  -DBoost_INCLUDE_DIR=$HOME/boost_1_77_0 \
  -DTTK_ENABLE_CPU_OPTIMIZATIONS=OFF \
  -DTTK_ENABLE_KAMIKAZE=ON \
  -DCMAKE_INSTALL_PREFIX=$HOME/install_pv56 \
  -DCMAKE_BUILD_TYPE=Release \
  ../ttk-0.9.7
```

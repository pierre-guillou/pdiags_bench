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

# ParaView

* GCC and Python
  + module load gcc/8.2
  + CC=gcc CXX=g++ ccmake -DPARAVIEW_USE_QT=OFF -DCMAKE_INSTALL_PREFIX=$HOME/install ..

# TTK with OpenMP

* GCC and SGI MPT
  + module load gcc/8.2 mpt/2.18
  + CC=gcc CXX=g++ ccmake -DTTK_ENABLE_CPU_OPTIMIZATIONS=OFF..

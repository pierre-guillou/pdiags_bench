HowTo: Run TTK on the MeSU HPC platform
=======================================

[MeSU](https://hpcave.upmc.fr/) is an HPC platform hosted by Sorbonne
Université. [Three
clusters](https://hpcave.upmc.fr/index.php/resources/mesu-supercomputer/)
are available.

* MeSU alpha is a shared-memory machine:
  - 1024 Intel Sandy Bridge cores
  - 16 TB RAM
  - 64 blades of 2 motherboards of 8 cores, 128 GB RAM
* MeSU beta is a distributed cluster:
  - 3456 Intel Haswell cores
  - 144 nodes of 24 cores, 128 GB RAM
* MeSU gamma is a GPU machine

Since TTK only implements shared memory parallelism, we are restricted
to either MeSU alpha or one node of MeSU beta.

MeSU uses a module system to provide a set of overlapping [software
libraries and
applications](https://hpcave.upmc.fr/index.php/usage/softwares/). However,
what is provided is not sufficient to get the whole TTK experience.

MeSU lets users connect to 'login nodes' on which software is built
and heavier computations can be submitted to a global queue to access
the full computational resources. Since several users share the login
nodes, it is recommanded not to use more than 4 cores during build.

To connect to MeSU, please fill the application form [available from
here](https://hpcave.upmc.fr/index.php/usage/open-an-account/), get a
signature from Julien and submit a scan to the MeSU administrators
using the aforementioned link.

Before anything, I recommand to read the the MeSU [QuickStart
Guide](https://hpcave.upmc.fr/index.php/usage/get-started/).

To run TTK onto MeSU, the first step is to build an up-to-date CMake
since the one provided by MeSU (3.5) is too old (but can still build
newer CMakes). The second is to build an up-to-date Python interpreter
(because the provided Python 3.4 might be too old too). Then, ParaView
and TTK.

0. Environment variables
========================

We will install everything in the `$HOME/install` prefix. Put the
following environment variables in your `.bashrc` or `.zshrc` (alter
the `TTK_BUILD` or the `PY39` variables after installation if needed):

```sh
TTK_BUILD=$HOME/ttk/build
INSTALL=$HOME/install
PY39=python3.9/site-packages
export PATH=$INSTALL/bin:$TTK_BUILD/bin:$PATH
export LD_LIBRARY_PATH=$INSTALL/lib64:$INSTALL/lib:$TTK_BUILD/lib64:$LD_LIBRARY_PATH
export CMAKE_PREFIX_PATH=$INSTALL/lib64/cmake:$CMAKE_PREFIX_PATH
export PYTHONPATH=$INSTALL/lib64/$PY39:$INSTALL/lib/$PY39:$TTK_BUILD/lib64/$PY39:/usr/lib/python3.4/site-packages
export PV_PLUGIN_PATH=$TTK_BUILD/lib64/TopologyToolKit
```

(We need to keep the system Python 3.4 in our `PYTHONPATH` otherwise
the provided PBS tools may not work correctly).

1. Build & install CMake
------------------------

Download any up-to-date CMake source package for Linux (e.g. [CMake
3.19.5](https://github.com/Kitware/CMake/releases/download/v3.19.5/cmake-3.19.5.tar.gz)). Untar,
create a build directory and call the system CMake with

```sh
cd cmake
mkdir build
cd build
cmake -DCMAKE_INSTALL_PREFIX=$HOME/install ..
make -j4 install
```

2. Build & install Python
-------------------------

Same as CMake, download any Python source (e.g. [Python
3.9.2](https://www.python.org/ftp/python/3.9.2/Python-3.9.2.tgz)). Use
the configure script to specify the install directory. Since it will
be used at run-time, we can also use the latest GCC available and
enable optimizations.

```sh
module load gcc
cd Python-3.9.2
CC=gcc CXX=g++ ./configure --enable-optimizations --prefix=$HOME/install
make -j4 install
```

3. Build & install ParaView
---------------------------

We will use the pre-patched `ttk-paraview` repository and we will
disable its graphical interface.

```sh
module load gcc
git clone --depth 1 https://github.com/topology-tool-kit/ttk-paraview
cd ttk-paraview
mkdir build
cd build
CC=gcc CXX=g++ ccmake -DPARAVIEW_USE_QT=OFF -DCMAKE_INSTALL_PREFIX=$HOME/install ..
make -j4 install
```

4. Build TTK
------------

This time, we will skip the install step. Since MeSU alpha uses old
Intel Sandy Bridge CPUs, we need to disable the CPU optimizations. To
compensate, we can enable the Kamikaze mode.

```sh
module load gcc
git clone https://github.com/topology-tool-kit/ttk
cd ttk
mkdir build
cd build
CC=gcc CXX=g++ ccmake -DTTK_ENABLE_CPU_OPTIMIZATIONS=OFF -DTTK_ENABLE_KAMIKAZE=ON ..
make -j4
```

5. Launch some TTK pipeline/standalone on MeSU
----------------------------------------------

With everything above done, we can check if our setup works
correctly. Open a Python console with `python` and check that it
displays the version we previously built. In this console, we can try

```py
import vtk
import topologytoolkit
```

to check if the environment variables are correct.

To submit a computation to the queue system, we use PBS and shell
scripts. The following is an example PBS script that will compute a
persistence diagram using the relevant TTK standalone on 64 cores of
MeSU alpha:

```sh
#!/bin/bash
#PBS -S /bin/bash
#PBS -q alpha
#PBS -l select=1:ncpus=64
#PBS -l walltime=00:05:00
#PBS -N job_name
#PBS -j oe

# load appropriate modules
module purge
module load mpt gcc

# move to PBS_O_WORKDIR
cd $PBS_O_WORKDIR

# Define scratch space
SCRATCH=/scratchalpha/$USER/
mkdir -p $SCRATCH

# env variables
INSTALL=$HOME/install
TTK_BUILD=$HOME/ttk/build
PY39=python3.9/site-packages
export LD_LIBRARY_PATH=$INSTALL/lib64:$INSTALL/lib:$TTK_BUILD/lib64:$LD_LIBARY_PATH
export PATH=$INSTALL/bin:$TTK_BUILD/bin:$PATH
export PYTHONPATH=$INSTALL/lib64/$PY39:$INSTALL/lib/$PY39:$TTK_BUILD/lib64/$PY39
export PV_PLUGIN_PATH=$TTK_BUILD/lib64/TopologyToolKit

# execute your program
cd $SCRATCH || exit 1

# copy input dataset
cp $PBS_O_WORKDIR/data.vti $SCRATCH

omplace -nt $NCPUS \
        ttkPersistenceDiagramCmd -i $SCRATCH/data.vti -t $NCPUS \
        1>> ${PBS_JOBID}.out 2>> ${PBS_JOBID}.err

# copy back diagram + log
cp ${PBS_JOBID}.out ${PBS_JOBID}.err output_port_0.vtu $PBS_O_WORKDIR || exit 1

# clean the temporary directory
rm -rf "$SCRATCH"/*
```

With this script, the computation can be launched with PBS:

```sh
qsub script.sh
```

Other PBS commands include:

* `qdel` to cancel a running job
* `qinfo` to check the status of the cluster
* `qstat` and `qmon` to see the global queue
* `tracejob *jobid*` and `qstat -fx *jobid*` to see the
  state of a particular job.
* `qreport` to get the yearly user ressource usage

More info about the syntax of the launch script on the MeSU [QuickStart
Guide](https://hpcave.upmc.fr/index.php/usage/get-started/).

Some things worth mentionning:

* `#PBS -S /bin/bash` is needed in addition to `#!/bin/bash` if you
  don't use bash as the default shell
* `$NCPUS` stores the number of requested CPUs
* I used SGI's mpt module and the `omplace` command to pin OpenMP
  threads to the CPU cores. It seemed to give a performance boost.
* the scratch filesystem is not limited by the 30 GB quota of user's
  home directories.
* this scratch filesystem is user-modifiable: you can `cd` into it to
  clean it manually.

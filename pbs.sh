#!/bin/bash
#PBS -S /bin/bash
#PBS -q alpha
#PBS -l select=1:ncpus=64
#PBS -l walltime=00:05:00
#PBS -N dipha_bench
#PBS -j oe

# load appropriate modules
module purge
# mpt must be loaded before openMPI to avoid mixing MPI implementations
module load mpt openMPI gcc

# move to PBS_O_WORKDIR
cd $PBS_O_WORKDIR

# Define scratch space
PROJECT=dipha
SCRATCH=/scratchalpha/$USER/$PROJECT
mkdir -p $SCRATCH

# working directory
WD=$HOME/pdiags_bench
# dataset
DS=aneurism_256x256x256_uint8_order_sfnorm_impl

# copy some input files to  $SCRATCH directory
cp $WD/datasets/*  $SCRATCH

# env variables
INSTDIR=/home/guilloup/install
TTK_BUILD=/home/guilloup/ttk-guillou/build
PY38=python3.8/site-packages
export LD_LIBRARY_PATH=$INSTDIR/lib64:$INSTDIR/lib:$TTK_BUILD/lib64:$LD_LIBARY_PATH
export PATH=$INSTDIR/bin:$WD/build_dipha:$TTK_BUILD/bin:$PATH
export PYTHONPATH=$INSTDIR/lib64/$PY38:$INSTDIR/lib/$PY38:$TTK_BUILD/lib64/$PY38
export PV_PLUGIN_PATH=$TTK_BUILD/lib64/TopologyToolKit

# execute your program
cd $SCRATCH || exit 1

omplace -nt 64 \
        ttkPersistenceDiagramCmd \
        -i $DS.vti -t 64 \
        1> $PBS_JOBNAME.out 2> $PBS_JOBNAME.err

mpirun -np 64 --oversubscribe \
       dipha \
       --benchmark \
       --upper_dim 3 \
       $DS.dipha output.dipha \
       1>> $PBS_JOBNAME.out 2>> $PBS_JOBNAME.err

# copy some output files to submission directory
cp -p output_port_0.vtu output.dipha $PBS_JOBNAME.out $PBS_JOBNAME.err $PBS_O_WORKDIR || exit 1

# clean the temporary directory
rm -rf "$SCRATCH"/*

#!/bin/bash
#PBS -q alpha
#PBS -l select=1:ncpus=64
#PBS -l walltime=00:05:00
#PBS -N dipha_bench

#load appropriate modules
module purge
module load gcc/8.2 openMPI/4.0.3

#move to PBS_O_WORKDIR
cd $PBS_O_WORKDIR

# Define scratch space
PROJECT=dipha
SCRATCH=/scratchalpha/$USER/$PROJECT
mkdir -p $SCRATCH

# working directory
WD=$HOME/pdiags_bench
# dataset
DS=aneurism_256x256x256_uint8_order_sfnorm_impl.dipha

# copy some input files to  $SCRATCH directory
cp $WD/datasets/$DS  $SCRATCH

#execute your program
cd $SCRATCH || exit 1
mpirun -np 64 \
       $WD/build_dipha/dipha \
       --benchmark \
       --upper_dim 3 \
       1> dipha.out 2> dipha.err \
       $DS output.dipha

# copy some output files to submittion directory and delete temporary work files
cp -p output.dipha dipha.out dipha.err $PBS_O_WORKDIR || exit 1

#clean the temporary directory
rm -rf "$SCRATCH”/*

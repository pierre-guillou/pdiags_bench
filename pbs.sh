#!/bin/bash
#PBS -S /bin/bash
#PBS -q alpha
#PBS -l select=1:ncpus=64
#PBS -l walltime=00:05:00
#PBS -N dipha_bench
#PBS -j oe

#load appropriate modules
module purge
module load openMPI

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
mpirun -np 64 --oversubscribe \
       $WD/build_dipha/dipha \
       --benchmark \
       --upper_dim 3 \
       $DS output.dipha \
       1> $PBS_JOBNAME.out 2> $PBS_JOBNAME.err \

# copy some output files to submittion directory and delete temporary work files
cp -p output.dipha $PBS_JOBNAME.out $PBS_JOBNAME.err $PBS_O_WORKDIR || exit 1

#clean the temporary directory
rm -rf "$SCRATCH"/*

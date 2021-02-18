#!/bin/bash
#PBS -S /bin/bash
#PBS -q alpha
#PBS -l select=1:ncpus=64
#PBS -l walltime=00:05:00
#PBS -N ttk_bench
#PBS -j oe

#load appropriate modules
module purge
module load gcc/8.2 mpt/2.18

#move to PBS_O_WORKDIR
cd $PBS_O_WORKDIR

# Define scratch space
PROJECT=dipha
SCRATCH=/scratchalpha/$USER/$PROJECT
mkdir -p $SCRATCH

# working directory
WD=$HOME/pdiags_bench
# dataset
DS=aneurism_256x256x256_uint8_order_sfnorm_impl.vti

# copy some input files to  $SCRATCH directory
cp $WD/datasets/$DS  $SCRATCH

#execute your program
cd $SCRATCH || exit 1
LD_LIBRARY_PATH=/home/guilloup/install/lib64:/home/guilloup/install/lib:/home/guilloup/ttk-guillou/build/lib64:$LD_LIBARY_PATH \
omplace -nt 64 \
    $HOME/ttk-guillou/build/bin/ttkPersistenceDiagramCmd \
    -i $DS -t 64 \
    1> $PBS_JOBNAME.out 2> $PBS_JOBNAME.err \

# copy some output files to submittion directory and delete temporary work files
cp -p output_port_0.vtu $PBS_JOBNAME.out $PBS_JOBNAME.err $PBS_O_WORKDIR || exit 1

#clean the temporary directory
rm -rf "$SCRATCH"/*

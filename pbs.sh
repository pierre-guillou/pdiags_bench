#!/bin/bash
#PBS -S /bin/bash
#PBS -q alpha
#PBS -l select=1:ncpus=128
#PBS -l walltime=00:50:00
#PBS -N dipha_bench
#PBS -j oe

# load appropriate modules
module purge
# mpt must be loaded before openMPI to avoid mixing MPI implementations
module load mpt openMPI/4.1.2-gcc112 gcc/11.2 python/3.9

# move to PBS_O_WORKDIR
cd $PBS_O_WORKDIR

# Define scratch space
PROJECT=dipha
SCRATCH=/scratchalpha/$USER/$PROJECT
mkdir -p $SCRATCH

# working directory
WD=$HOME/pdiags_bench
mkdir -p $WD/log

# copy some input files to  $SCRATCH directory
cp -r $WD/raws $SCRATCH

# env variables
source $HOME/env.sh

# execute your program
cd $SCRATCH || exit 1

# prepare datasets
mkdir datasets

for raw in raws/*.raw; do
    raw_stem=${raw#raws/}
    out=$WD/log/${raw_stem}_${PBS_JOBID}.out
    err=$WD/log/${raw_stem}_${PBS_JOBID}.err

    echo "Converting $raw..." 1> $out 2> $err
    python3 $WD/convert_datasets.py -d datasets $raw 1> $out 2> $out

    for nt in 1 32 64 128; do
        for vtu in datasets/*.vtu; do
            echo "Processing $vtu with TTK with $nt threads..." >> $out
            omplace -nt $nt \
                 ttkPersistenceDiagramCmd -B 2 -d 4 -i $vtu -t $nt \
                 1>> $out 2>> $err
        done

        sleep 5                 # flush?

        for dph in datasets/*.dipha; do
            echo "Processing $dph with Dipha with $nt processes..." >> $out
            mpirun -np $nt --oversubscribe \
                 dipha --benchmark $dph out.dipha \
                 1>> $out 2>> $err
        done

        sleep 5                 # flush?
    done

    rm datasets/*
done

# copy some output files to submission directory
# cp -p $PBS_JOBNAME.out $PBS_JOBNAME.err $PBS_O_WORKDIR || exit 1

# clean the temporary directory
rm -rf "$SCRATCH"/*

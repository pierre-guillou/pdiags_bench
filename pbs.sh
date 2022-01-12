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
    echo "Converting $raw..."
    time python3 $WD/convert_datasets.py -d datasets $raw
done

for vtu in datasets/*.vtu; do
    vtu_stem=${vtu#datasets/}
    out=$WD/log/${vtu_stem}_${PBS_JOBID}_${NCPUS}.out
    err=$WD/log/${vtu_stem}_${PBS_JOBID}_${NCPUS}.err
    for nt in 1 32 64 96 128; do
        echo "Processing $vtu with TTK with $nt threads..." >> $out
        omplace -nt $nt \
                ttkPersistenceDiagramCmd -B 2 -d 4 -i $vtu -t $nt \
                1>> $out 2>> $err
    done
    rm $vtu
done

for dph in datasets/*.dipha; do
    dph_stem=${dph#datasets/}
    out=$WD/log/${dph_stem}_${PBS_JOBID}_${NCPUS}.out
    err=$WD/log/${dph_stem}_${PBS_JOBID}_${NCPUS}.err
    for np in 1 32 64 96 128; do
        echo "Processing $dph with Dipha with $np processes..." >> $out
        mpirun -np $np --oversubscribe \
               dipha --benchmark $dph out.dipha \
               1>> $out 2>> $err
    done
    rm $dph
done

# copy some output files to submission directory
# cp -p $PBS_JOBNAME.out $PBS_JOBNAME.err $PBS_O_WORKDIR || exit 1

# clean the temporary directory
rm -rf "$SCRATCH"/*

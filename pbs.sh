#!/bin/bash
#PBS -S /bin/bash
#PBS -q alpha
#PBS -l select=1:ncpus=64
#PBS -l walltime=00:50:00
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

# copy some input files to  $SCRATCH directory
cp -r $WD/raws $SCRATCH

# env variables
INSTDIR=/home/guilloup/install
TTK_BUILD=/home/guilloup/ttk-guillou/build
PY38=python3.8/site-packages
export LD_LIBRARY_PATH=$INSTDIR/lib64:$INSTDIR/lib:$TTK_BUILD/lib64:$LD_LIBARY_PATH
export PATH=$INSTDIR/bin:$WD/build_dipha:$TTK_BUILD/bin:$PATH
export PYTHONPATH=$INSTDIR/lib64/$PY38:$INSTDIR/lib/$PY38:$TTK_BUILD/lib64/$PY38
export PV_PLUGIN_PATH=$TTK_BUILD/lib64/TopologyToolKit
nthreads=64
out=$WD/$PBS_JOBNAME.out
err=$WD/$PBS_JOBNAME.err

# clean log files
rm $out $err

# execute your program
cd $SCRATCH || exit 1

# prepare datasets
mkdir datasets

for raw in raws/*.raw; do
    echo "Converting $raw..."
    time python $WD/convert_datasets.py $raw datasets
    raw_stem=${raw#raws/}
    vtu=datasets/${raw_stem%.raw}_order_expl.vtu
    echo "Processing $vtu with TTK..." >> $out
    omplace -nt $nthreads \
            python $WD/compute_diag_ttk.py $vtu $nthreads \
            1>> $out 2>> $err
    dipha=${vtu%.vtu}.dipha
    echo "Processing $dipha with Dipha..." >> $out
    mpirun -np $nthreads --oversubscribe \
           dipha --benchmark --upper_dim 3 $dipha output.dipha \
           1>> $out 2>> $err
done

# copy some output files to submission directory
# cp -p $PBS_JOBNAME.out $PBS_JOBNAME.err $PBS_O_WORKDIR || exit 1

# clean the temporary directory
rm -rf "$SCRATCH"/*

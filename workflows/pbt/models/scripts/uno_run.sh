#! /usr/bin/env bash
set -eu

THIS=$( cd $( dirname $0 ) ; /bin/pwd )

BENCHMARKS=$HOME/Documents/repos/Benchmarks
SUPERVISOR=$PWD/../../../..

PYTHONPATH=$BENCHMARKS/Pilot1/common
PYTHONPATH+=":$BENCHMARKS/common"
PYTHONPATH+=":$SUPERVISOR/workflows/common/python"

export PYTHONPATH=$PYTHONPATH

python $THIS/../uno/uno_baseline_keras2.py --conf $THIS/../uno/uno_perf_bench_model.txt

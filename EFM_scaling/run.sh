#!/bin/bash
# EFM Scaling Experiments - run all topology/benchmark combinations

# Allreduce (count=256)
python3 run_scaling_experiments.py --topo-name DDF     --benchmark Allreduce --problem-size 256 --num-threads 6
python3 run_scaling_experiments.py --topo-name Slimfly --benchmark Allreduce --problem-size 256 --num-threads 6
python3 run_scaling_experiments.py --topo-name Polarfly --benchmark Allreduce --problem-size 256 --num-threads 6

# Alltoall (bytes=64)
python3 run_scaling_experiments.py --topo-name DDF     --benchmark Alltoall --problem-size 64 --num-threads 6
python3 run_scaling_experiments.py --topo-name Slimfly --benchmark Alltoall --problem-size 64 --num-threads 6
python3 run_scaling_experiments.py --topo-name Polarfly --benchmark Alltoall --problem-size 64 --num-threads 6

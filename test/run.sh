#!/bin/bash

export PICKLED_DATA="$(pwd)/../pickled_data"

sst -n 10 smallest_ddf_debug.py

# cd /users/ziyzhang/SST/experiments/comparison_group_1_realistic/jellyfish
# bash sweep.sh

# cd /users/ziyzhang/SST/experiments/comparison_group_2_realistic/slimfly
# bash sweep.sh

# cd /users/ziyzhang/SST/experiments/comparison_group_2_realistic/jellyfish
# bash sweep.sh

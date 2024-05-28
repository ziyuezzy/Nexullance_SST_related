#!/bin/bash

# List of LOAD values to sweep through
# load_values=(0.01)
load_values=(0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0)

# Loop over the list of LOAD values and execute the Python script
for load in "${load_values[@]}"; do
    sed -i "s/LOAD=.*/LOAD=$load/" config.py
    sst -n 10 config.py
done

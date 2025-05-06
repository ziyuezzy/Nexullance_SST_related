This is a repository for simulating HPC networks with SST-Toolkit.
Three sst-elements: Ember, Firefly, and Merlin are used in the setup. Please refer to the images in ./doc for better understanding what they do.

For using, first run ./setup.sh.

Make that sst-core (https://github.com/sstsimulator/sst-core) and sst-element (https://github.com/ziyuezzy/sst-elements) are installed, and the installed bin path is added to env variable $PATH (e.g., in '~/.bashrc')

## subdir "./Merlin_experiements/"

The scripts are used to generate data (run sst simulation) and generate figure 6 in the paper

## subdir "./EFM_experiments/"

The scripts are used to generate data (run sst simulation) and generate figure 7 in the paper

## subdir "./MD_scaling/"

The scripts are used to generate data (run sst simulation) and generate figure 8 in the paper
This is a repository for simulating HPC networks with SST-Toolkit.
Three sst-elements: Ember, Firefly, and Merlin are used in the setup. Please refer to the images in ./doc for better understanding what they do.

For using/reproducing, first run ./setup.sh.

Make sure you have installed the sst-core and sst-element (from_graph fork)


<!-- TODOs:  -->

1. explore the impact of increasing EPR and CPE on the traffic pattern.

2. explore the effectiveness of nexullance results, compared to ugal.

3. use flow-level modeling to calculate network throughput, compare with flit and message level simualations

4. run a benchmark for three modeling approaches: flit-level, message-level, and flow-level.

try ddf 36: change EPR and the routing algorithm
try other topologies



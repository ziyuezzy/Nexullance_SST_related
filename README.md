This is a repository for simulating HPC networks with SST-Toolkit.
Three sst-elements: Ember, Firefly, and Merlin are used in the setup. Please refer to the images in ./doc for better understanding what they do.

For using/reproducing, first run ./setup.sh.

Make sure you have installed the sst-core and sst-element (from_graph fork)


<!-- TODOs:  -->

try ddf 36: change EPR and the routing algorithm
try other topologies

observation: one core can only send (and also receive) one packet at a time, it seems to make sense
But why such long delay? (almost 1000ns?)  -> the large delay has been removed, but which one is more real? Can we test this by running a real MPI app?

# TODO: things to write down:
1. methods of traffic visualization
2. Observations of traffic patterns from basic or complex Ember Motifs
3. Experiments on different bench parameters, and routing algorithms
4. talk about Nexullance
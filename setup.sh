pip install numpy matplotlib networkx joblib galois # pre-request python3 libs
git submodule update --init --recursive

# generate python pickle files for SST simulation, these will not be tracked by git
mkdir pickled_data
cd pickled_data
mkdir from_graph_edgelists
mkdir from_graph_pathdicts
mkdir from_graph_pass_down

export PICKLED_DATA="$(pwd)/pickled_data"

# setup the python path, for easy import
export PYTHONPATH=$(pwd):$PYTHONPATH
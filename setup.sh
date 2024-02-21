pip install numpy matplotlib networkx joblib galois # pre-request python3 libs
git clone https://github.ugent.be/ziyzhang/topology-research

# generate python pickle files for SST
mkdir pickled_data
cd pickled_data
mkdir from_graph_edgelists
mkdir from_graph_pathdicts
mkdir from_graph_pass_down

export PICKLED_DATA="$pwd/pickled_data"
